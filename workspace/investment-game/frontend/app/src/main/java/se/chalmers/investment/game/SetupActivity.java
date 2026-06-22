package se.chalmers.investment.game;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.admin.DevicePolicyManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;

import org.json.JSONObject;

import java.util.regex.Pattern;

import se.chalmers.investment.game.api.ApiPromise;
import se.chalmers.investment.game.api.ApiRequest;
import se.chalmers.investment.game.api.ApiResult;
import se.chalmers.investment.game.api.types.ConfigureParticipantResponse;

public class SetupActivity extends Activity {
    private static final Pattern IP_PATTERN =
            Pattern.compile(
                    "^((25[0-5]|2[0-4]\\d|1\\d{2}|[1-9]?\\d)\\.){3}" +
                            "(25[0-5]|2[0-4]\\d|1\\d{2}|[1-9]?\\d)$"
            );

    private EditText ipInput;
    private EditText participantInput;

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

        ipInput = findViewById(R.id.ip);
        participantInput = findViewById(R.id.participant_id);

        ipInput.setSelection(ipInput.getText().length());
        Button button = findViewById(R.id.connect);

        button.setOnClickListener(v -> attemptConnection());
    }

    private void attemptConnection() {
        String ip = ipInput.getText().toString().trim();
        String participantId = participantInput.getText().toString().trim();

        if (!IP_PATTERN.matcher(ip).matches()) {
            Toast.makeText(this, "Invalid IP address", Toast.LENGTH_SHORT).show();

            return;
        }

        if (participantId.isEmpty()) {
            Toast.makeText(this, "Participant ID is required", Toast.LENGTH_SHORT).show();

            return;
        }

        ApiRequest.setBaseUrl(ip);

        configureParticipant(participantId, false);
    }

    private void configureParticipant(String participantId, boolean override) {
        JSONObject body = new JSONObject();

        try {
            body.put("participant_id", participantId);
            body.put("override", override);
        } catch (Exception exception) {
            Toast.makeText(this, "Could not prepare request", Toast.LENGTH_SHORT).show();
            return;
        }

        ApiRequest.post(this,
                "/configure-participant",
                body,
                ConfigureParticipantResponse.class,
                new ApiPromise<ConfigureParticipantResponse>() {
            @Override
            public void onSuccess(ConfigureParticipantResponse data) {
                Intent intent = new Intent(SetupActivity.this, MainActivity.class);
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);

                startActivity(intent);
                finish();
            }

            @Override
            public void onError(ApiResult<ConfigureParticipantResponse> error) {
                if (error.code == 409 && requiresOverride(error.error)) {
                    promptOverride(participantId);
                    return;
                }

                String message = parseErrorMessage(error.error);
                if (message == null || message.isEmpty()) {
                    message = "Could not configure participant";
                }

                Toast.makeText(SetupActivity.this, message, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void promptOverride(String participantId) {
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Participant already run")
                .setMessage("A conversation file already exists for this participant.\nOverride and continue?")
                .setNegativeButton("Override", (d, which) -> configureParticipant(participantId, true))
                .setPositiveButton("Cancel", null)
                .show();

        Button positive = dialog.getButton(AlertDialog.BUTTON_POSITIVE);
        Button negative = dialog.getButton(AlertDialog.BUTTON_NEGATIVE);

        positive.setBackgroundResource(R.drawable.dialog_positive_button);
        positive.setTextColor(Color.BLACK);

        negative.setBackgroundResource(R.drawable.dialog_negative_button);
        negative.setTextColor(Color.parseColor("#8B0000"));
        negative.setTypeface(null, Typeface.BOLD);
    }

    private boolean requiresOverride(String rawError) {
        try {
            JSONObject json = new JSONObject(rawError);
            return json.optBoolean("override_required", false);
        } catch (Exception ignored) {
            return false;
        }
    }

    private String parseErrorMessage(String rawError) {
        if (rawError == null) {
            return null;
        }

        try {
            JSONObject json = new JSONObject(rawError);
            String error = json.optString("error", "");
            if (!error.isEmpty()) {
                return error;
            }

            return json.optString("description", rawError);
        } catch (Exception ignored) {
            return rawError;
        }
    }
}
