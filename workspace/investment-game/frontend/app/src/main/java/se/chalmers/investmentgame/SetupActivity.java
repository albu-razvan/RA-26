package se.chalmers.investmentgame;

import android.app.Activity;
import android.app.admin.DevicePolicyManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;

import java.util.regex.Pattern;

import se.chalmers.investmentgame.api.ApiPromise;
import se.chalmers.investmentgame.api.ApiRequest;
import se.chalmers.investmentgame.api.ApiResult;

public class SetupActivity extends Activity {
    private static final Pattern IP_PATTERN =
            Pattern.compile(
                    "^((25[0-5]|2[0-4]\\d|1\\d{2}|[1-9]?\\d)\\.){3}" +
                            "(25[0-5]|2[0-4]\\d|1\\d{2}|[1-9]?\\d)$"
            );

    private EditText input;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        DevicePolicyManager devicePolicyManager =
                (DevicePolicyManager) getSystemService(Context.DEVICE_POLICY_SERVICE);
        ComponentName adminComponent = new ComponentName(this, GameDeviceAdminReceiver.class);

        if (devicePolicyManager.isDeviceOwnerApp(getPackageName())) {
            devicePolicyManager.setLockTaskPackages(adminComponent, new String[]{getPackageName()});
        } else {
            String message = "App is not a Device Owner. Did you read the README ಠಿ_ಠ?";

            Toast.makeText(this, message, Toast.LENGTH_LONG).show();
            finishAndRemoveTask();
        }

        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_setup);

        input = findViewById(R.id.ip);
        Button button = findViewById(R.id.connect);

        button.setOnClickListener(v -> attemptConnection());
    }

    private void attemptConnection() {
        String ip = input.getText().toString().trim();

        if (!IP_PATTERN.matcher(ip).matches()) {
            Toast.makeText(this, "Invalid IP address", Toast.LENGTH_SHORT).show();

            return;
        }

        ApiRequest.setBaseUrl(ip);
        ApiRequest.get(this, "/status", Object.class, new ApiPromise<Object>() {
            @Override
            public void onSuccess(Object data) {
                Intent intent = new Intent(SetupActivity.this, MainActivity.class);
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);

                startActivity(intent);
                finish();
            }

            @Override
            public void onError(ApiResult<Object> error) {
                Toast.makeText(SetupActivity.this,
                        "Could not connect to server", Toast.LENGTH_SHORT).show();
            }
        });
    }
}