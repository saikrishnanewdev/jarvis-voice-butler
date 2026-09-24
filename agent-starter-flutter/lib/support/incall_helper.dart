import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

class InCallHelper {
  static const MethodChannel _channel = MethodChannel('com.livekit.jarvis/incall');

  static void initialize({
    required VoidCallback onCallStarted,
    required VoidCallback onCallEnded,
  }) {
    _channel.setMethodCallHandler((call) async {
      if (call.method == 'onCellularCallStateChanged') {
        final Map<dynamic, dynamic> args = call.arguments as Map<dynamic, dynamic>;
        final bool active = args['active'] as bool? ?? false;
        debugPrint('Cellular call state changed in Flutter: active=$active');
        if (active) {
          onCallStarted();
        } else {
          onCallEnded();
        }
      }
    });
  }

  static Future<bool> isDefaultDialer() async {
    try {
      final bool result = await _channel.invokeMethod('isDefaultDialer') ?? false;
      return result;
    } catch (e) {
      debugPrint('Error checking default dialer: $e');
      return false;
    }
  }

  static Future<void> requestDefaultDialer() async {
    try {
      await _channel.invokeMethod('requestDefaultDialer');
    } catch (e) {
      debugPrint('Error requesting default dialer: $e');
    }
  }
}
