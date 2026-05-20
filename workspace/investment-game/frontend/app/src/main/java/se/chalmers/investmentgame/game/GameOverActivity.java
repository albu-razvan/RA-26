package se.chalmers.investmentgame.game;

import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;

import androidx.annotation.Nullable;

import se.chalmers.investmentgame.R;
import se.chalmers.investmentgame.api.ApiPromise;
import se.chalmers.investmentgame.api.ApiRequest;
import se.chalmers.investmentgame.api.ApiResult;
import se.chalmers.investmentgame.utils.KioskActivity;

public class GameOverActivity extends KioskActivity {
    public static final String BANK_INTENT_KEY = "BankGameValue";
    private static final String TAG = "GameOverActivity";

    private boolean resetRequested;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(R.layout.activity_game_over);

        ((TextView) findViewById(R.id.bank)).setText(String.valueOf(getIntent()
                .getIntExtra(BANK_INTENT_KEY, 0)));

        findViewById(R.id.finish_game_over).setOnClickListener(view -> finish());
    }

    @Override
    protected boolean isBackPressEnabled() {
        return true;
    }

    @Override
    protected void onStop() {
        super.onStop();

        if (resetRequested) {
            return;
        }

        resetRequested = true;
        ApiRequest.post(getApplicationContext(), "/reset-game", Object.class,
                new ApiPromise<Object>() {
                    @Override
                    public void onSuccess(Object data) {
                    }

                    @Override
                    public void onError(ApiResult<Object> error) {
                        Log.w(TAG, "Failed to reset game state: " + error.error);
                    }
                });
    }
}
