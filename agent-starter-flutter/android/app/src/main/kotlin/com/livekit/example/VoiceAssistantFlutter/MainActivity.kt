package com.livekit.example.VoiceAssistantFlutter

import android.app.role.RoleManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.telecom.TelecomManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    companion object {
        private const val CHANNEL = "com.livekit.jarvis/incall"
        private const val REQUEST_CODE_SET_DEFAULT_DIALER = 101
        private var instance: MainActivity? = null
        private var methodChannel: MethodChannel? = null

        fun notifyCallStateChanged(active: Boolean) {
            methodChannel?.invokeMethod("onCellularCallStateChanged", mapOf("active" to active))
            if (active && instance != null) {
                try {
                    val intent = Intent(instance, MainActivity::class.java).apply {
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
                    }
                    instance?.startActivity(intent)
                } catch (e: Exception) {
                    // Ignore if background launch restriction applies
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: android.os.Bundle?) {
        super.onCreate(savedInstanceState)
        instance = this
    }

    override fun onResume() {
        super.onResume()
        requestAllPermissions()
    }

    private fun requestAllPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val permissions = arrayOf(
                android.Manifest.permission.RECORD_AUDIO,
                android.Manifest.permission.READ_PHONE_STATE,
                android.Manifest.permission.ANSWER_PHONE_CALLS,
                android.Manifest.permission.CALL_PHONE
            )
            val missingPermissions = permissions.filter {
                checkSelfPermission(it) != android.content.pm.PackageManager.PERMISSION_GRANTED
            }
            if (missingPermissions.isNotEmpty()) {
                requestPermissions(missingPermissions.toTypedArray(), 102)
            }
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        methodChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)

        methodChannel?.setMethodCallHandler { call, result ->
            when (call.method) {
                "requestDefaultDialer" -> {
                    try {
                        requestAllPermissions()

                        var rolePromptShown = false
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                            val roleManager = getSystemService(Context.ROLE_SERVICE) as RoleManager
                            if (roleManager.isRoleAvailable(RoleManager.ROLE_DIALER) && !roleManager.isRoleHeld(RoleManager.ROLE_DIALER)) {
                                val intent = roleManager.createRequestRoleIntent(RoleManager.ROLE_DIALER)
                                startActivityForResult(intent, REQUEST_CODE_SET_DEFAULT_DIALER)
                                rolePromptShown = true
                            }
                        }

                        if (!rolePromptShown) {
                            val telecomManager = getSystemService(Context.TELECOM_SERVICE) as TelecomManager
                            if (telecomManager.defaultDialerPackage != packageName) {
                                val intent = Intent(TelecomManager.ACTION_CHANGE_DEFAULT_DIALER).apply {
                                    putExtra(TelecomManager.EXTRA_CHANGE_DEFAULT_DIALER_PACKAGE_NAME, packageName)
                                }
                                startActivity(intent)
                            } else {
                                openDefaultAppSettings()
                            }
                        }
                        result.success(true)
                    } catch (e: Exception) {
                        openDefaultAppSettings()
                        result.success(true)
                    }
                }
                "isDefaultDialer" -> {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        val roleManager = getSystemService(Context.ROLE_SERVICE) as RoleManager
                        result.success(roleManager.isRoleHeld(RoleManager.ROLE_DIALER))
                    } else {
                        val telecomManager = getSystemService(Context.TELECOM_SERVICE) as TelecomManager
                        result.success(telecomManager.defaultDialerPackage == packageName)
                    }
                }
                else -> result.notImplemented()
            }
        }
    }

    private fun openDefaultAppSettings() {
        try {
            val intent = Intent(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS)
            startActivity(intent)
        } catch (e: Exception) {
            val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.fromParts("package", packageName, null)
            }
            startActivity(intent)
        }
    }
}
