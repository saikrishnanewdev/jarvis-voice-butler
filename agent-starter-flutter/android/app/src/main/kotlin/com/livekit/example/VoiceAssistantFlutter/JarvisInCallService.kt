package com.livekit.example.VoiceAssistantFlutter

import android.content.Context
import android.media.AudioManager
import android.telecom.Call
import android.telecom.CallAudioState
import android.telecom.InCallService
import android.telecom.VideoProfile
import android.util.Log

class JarvisInCallService : InCallService() {
    companion object {
        private const val TAG = "JarvisInCallService"
        var instance: JarvisInCallService? = null
        var activeCall: Call? = null
    }

    override fun onCallAdded(call: Call) {
        super.onCallAdded(call)
        instance = this
        activeCall = call
        Log.d(TAG, "Incoming cellular SIM call added: state=${call.state}")

        fun configureCallAudioAndConnect(c: Call) {
            try {
                val audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager
                
                // Explicitly unmute call & app microphone stream
                try {
                    setMuted(false)
                } catch (_: Exception) {}
                audioManager.isMicrophoneMute = false

                // Set volume streams to max so conversation is clear
                val maxVoiceVol = audioManager.getStreamMaxVolume(AudioManager.STREAM_VOICE_CALL)
                audioManager.setStreamVolume(AudioManager.STREAM_VOICE_CALL, maxVoiceVol, 0)
                
                val maxMusicVol = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
                audioManager.setStreamVolume(AudioManager.STREAM_MUSIC, maxMusicVol, 0)

                // Force speakerphone route
                setAudioRoute(CallAudioState.ROUTE_SPEAKER)
                audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
                audioManager.isSpeakerphoneOn = true

                // Re-enforce speakerphone route and unmute after 500ms
                android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                    try {
                        try {
                            setMuted(false)
                        } catch (_: Exception) {}
                        audioManager.isMicrophoneMute = false
                        setAudioRoute(CallAudioState.ROUTE_SPEAKER)
                        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
                        audioManager.isSpeakerphoneOn = true
                        Log.d(TAG, "Re-applied speakerphone route and unmuted successfully")
                    } catch (e: Exception) {
                        Log.e(TAG, "Delayed audio route error: ${e.message}")
                    }
                }, 500)

            } catch (e: Exception) {
                Log.e(TAG, "Error configuring call audio route: ${e.message}")
            }
            MainActivity.notifyCallStateChanged(true)
        }

        fun tryAutoAnswer(c: Call) {
            if (c.state == Call.STATE_RINGING) {
                Log.d(TAG, "Auto-answering incoming SIM call via Jarvis...")
                try {
                    c.answer(VideoProfile.STATE_AUDIO_ONLY)
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to auto-answer call", e)
                }
            } else if (c.state == Call.STATE_ACTIVE) {
                configureCallAudioAndConnect(c)
            }
        }

        tryAutoAnswer(call)

        call.registerCallback(object : Call.Callback() {
            override fun onStateChanged(call: Call, state: Int) {
                Log.d(TAG, "Call state changed: $state")
                if (state == Call.STATE_RINGING) {
                    tryAutoAnswer(call)
                } else if (state == Call.STATE_ACTIVE) {
                    configureCallAudioAndConnect(call)
                } else if (state == Call.STATE_DISCONNECTED || state == Call.STATE_DISCONNECTING) {
                    try {
                        val audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager
                        audioManager.mode = AudioManager.MODE_NORMAL
                        audioManager.isSpeakerphoneOn = false
                    } catch (_: Exception) {}
                    MainActivity.notifyCallStateChanged(false)
                    activeCall = null
                }
            }
        })
    }

    override fun onCallRemoved(call: Call) {
        super.onCallRemoved(call)
        Log.d(TAG, "Call removed")
        if (activeCall == call) {
            activeCall = null
            MainActivity.notifyCallStateChanged(false)
        }
    }
}
