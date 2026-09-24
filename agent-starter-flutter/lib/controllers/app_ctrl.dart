import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:livekit_client/livekit_client.dart' as sdk;
import 'package:livekit_components/livekit_components.dart' as components;
import 'package:logging/logging.dart';
import 'package:uuid/uuid.dart';
import 'package:dart_jsonwebtoken/dart_jsonwebtoken.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import '../support/incall_helper.dart';

final String homepageAgentTokenEndpoint = 'https://livekit.com/api/homepage-agent/token';

enum AppScreenState { welcome, agent }

enum AgentScreenState { visualizer, transcription }

class AppCtrl extends ChangeNotifier {
  static const uuid = Uuid();
  static final _logger = Logger('AppCtrl');

  // States
  AppScreenState appScreenState = AppScreenState.welcome;
  AgentScreenState agentScreenState = AgentScreenState.visualizer;

  //Test
  bool isUserCameEnabled = false;
  bool isScreenshareEnabled = false;

  final messageCtrl = TextEditingController();
  final messageFocusNode = FocusNode();

  late final sdk.Room room = sdk.Room(roomOptions: const sdk.RoomOptions(enableVisualizer: true));
  late final roomContext = components.RoomContext(room: room);
  late final sdk.Session session = _createSession(room: room);

  static sdk.Session _createSession({required sdk.Room room}) {
    final livekitUrl = dotenv.env['LIVEKIT_URL']?.replaceAll('"', '').trim() ?? 'wss://test-te00laqm.livekit.cloud';
    final apiKey = dotenv.env['LIVEKIT_API_KEY']?.replaceAll('"', '').trim() ?? 'APIwPJpAPzRd5nf';
    final apiSecret = dotenv.env['LIVEKIT_API_SECRET']?.replaceAll('"', '').trim() ?? '7s7zDdiqeiX3F2eLJJQPzuKK43b9ukTh7TzW34A64pX';
    final agentName = dotenv.env['LIVEKIT_AGENT_NAME']?.replaceAll('"', '').trim() ?? 'my-agent';

    final roomName = 'voice_assistant_room_${DateTime.now().millisecondsSinceEpoch % 10000}';
    final identity = 'voice_assistant_user_${DateTime.now().millisecondsSinceEpoch % 10000}';
    final nowSeconds = (DateTime.now().millisecondsSinceEpoch / 1000).floor();
    final nbfSeconds = nowSeconds - 60; // 60 seconds clock skew tolerance
    final expSeconds = nowSeconds + 7200; // 2 hours validity

    final payload = {
      'exp': expSeconds,
      'iss': apiKey,
      'nbf': nbfSeconds,
      'sub': identity,
      'name': 'user',
      'video': {
        'room': roomName,
        'roomJoin': true,
        'canPublish': true,
        'canSubscribe': true,
        'canPublishData': true,
      },
      'roomConfig': {
        'agents': [
          {
            'agentName': agentName,
          }
        ]
      }
    };

    final jwt = JWT(payload);
    final token = jwt.sign(SecretKey(apiSecret));

    return sdk.Session.fromFixedTokenSource(
      sdk.LiteralTokenSource(
        serverUrl: livekitUrl,
        participantToken: token,
      ),
      options: sdk.SessionOptions(room: room),
    );
  }

  bool isSendButtonEnabled = false;
  bool isSessionStarting = false;
  bool _hasCleanedUp = false;

  AppCtrl() {
    final format = DateFormat('HH:mm:ss');
    // configure logs for debugging
    Logger.root.level = Level.FINE;
    Logger.root.onRecord.listen((record) {
      debugPrint('${format.format(record.time)}: ${record.message}');
    });

    messageCtrl.addListener(() {
      final newValue = messageCtrl.text.isNotEmpty;
      if (newValue != isSendButtonEnabled) {
        isSendButtonEnabled = newValue;
        notifyListeners();
      }
    });

    session.addListener(_handleSessionChange);

    InCallHelper.initialize(
      onCallStarted: () {
        _logger.info('Cellular SIM call started. Connecting Jarvis voice session…');
        connect();
      },
      onCallEnded: () {
        _logger.info('Cellular SIM call ended. Disconnecting Jarvis voice session…');
        disconnect();
      },
    );
  }

  Future<void> cleanUp() async {
    if (_hasCleanedUp) return;
    _hasCleanedUp = true;

    session.removeListener(_handleSessionChange);
    await session.dispose();
    await room.dispose();
    roomContext.dispose();
    messageCtrl.dispose();
    messageFocusNode.dispose();
  }

  @override
  void dispose() {
    unawaited(cleanUp());
    super.dispose();
  }

  void sendMessage() async {
    isSendButtonEnabled = false;

    final text = messageCtrl.text;
    messageCtrl.clear();
    notifyListeners();

    if (text.isEmpty) return;
    await session.sendText(text);
  }

  void toggleUserCamera(components.MediaDeviceContext? deviceCtx) {
    isUserCameEnabled = !isUserCameEnabled;
    isUserCameEnabled ? deviceCtx?.enableCamera() : deviceCtx?.disableCamera();
    notifyListeners();
  }

  void toggleScreenShare() {
    isScreenshareEnabled = !isScreenshareEnabled;
    notifyListeners();
  }

  void toggleAgentScreenMode() {
    agentScreenState =
        agentScreenState == AgentScreenState.visualizer ? AgentScreenState.transcription : AgentScreenState.visualizer;
    notifyListeners();
  }

  void connect() async {
    if (isSessionStarting) {
      _logger.fine('Connection attempt ignored: session already starting.');
      return;
    }

    _logger.info('Starting session connection…');
    isSessionStarting = true;
    notifyListeners();

    try {
      await session.start();
      if (session.connectionState == sdk.ConnectionState.connected) {
        appScreenState = AppScreenState.agent;
        notifyListeners();
      }
    } catch (error, stackTrace) {
      _logger.severe('Connection error: $error', error, stackTrace);
      appScreenState = AppScreenState.welcome;
      notifyListeners();
    } finally {
      if (isSessionStarting) {
        isSessionStarting = false;
        notifyListeners();
      }
    }
  }

  Future<void> disconnect() async {
    await session.end();
    session.restoreMessageHistory(const []);
    appScreenState = AppScreenState.welcome;
    agentScreenState = AgentScreenState.visualizer;
    notifyListeners();
  }

  void _handleSessionChange() {
    final sdk.ConnectionState state = session.connectionState;
    AppScreenState? nextScreen;
    switch (state) {
      case sdk.ConnectionState.connected:
      case sdk.ConnectionState.reconnecting:
        nextScreen = AppScreenState.agent;
        break;
      case sdk.ConnectionState.disconnected:
        nextScreen = AppScreenState.welcome;
        break;
      case sdk.ConnectionState.connecting:
        nextScreen = null;
        break;
    }

    if (nextScreen != null && nextScreen != appScreenState) {
      appScreenState = nextScreen;
      notifyListeners();
    }
  }
}
