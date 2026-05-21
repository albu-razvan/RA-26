package se.chalmers.investmentgame;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import se.chalmers.investmentgame.api.ApiPromise;
import se.chalmers.investmentgame.api.ApiRequest;
import se.chalmers.investmentgame.api.ApiResult;
import se.chalmers.investmentgame.api.types.StatusResponse;
import se.chalmers.investmentgame.api.types.StartGameResponse;
import se.chalmers.investmentgame.game.GameActivity;
import se.chalmers.investmentgame.utils.KioskActivity;

public class MainActivity extends KioskActivity {
    private Button startButton;
    private boolean canStartGame = true;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(R.layout.activity_main);

        startButton = findViewById(R.id.start);

        startButton.setVisibility(android.view.View.INVISIBLE);

        startButton.setOnClickListener(view -> {
            if (!canStartGame) {
                return;
            }

            ApiRequest.post(this, "/start-game", StartGameResponse.class,
                    new ApiPromise<StartGameResponse>() {
                        @Override
                        public void onSuccess(StartGameResponse result) {
                            Intent intent = new Intent(MainActivity.this, GameActivity.class);
                            intent.putExtra(GameActivity.GAME_INTENT_KEY, result);

                            startActivity(intent);
                        }

                        @Override
                        public void onError(ApiResult<StartGameResponse> error) {
                            Toast.makeText(MainActivity.this,
                                    error.error, Toast.LENGTH_LONG).show();
                            refreshExperimentStatus();
                        }
                    });
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshExperimentStatus();
    }

    private void refreshExperimentStatus() {
        ApiRequest.get(this, "/status", StatusResponse.class, new ApiPromise<StatusResponse>() {
            @Override
            public void onSuccess(StatusResponse status) {
                canStartGame = status.getGamesRemaining() > 0;
                startButton.setEnabled(canStartGame);

                if (canStartGame) {
                    startButton.setText(status.getGamesPlayed() > 0
                            ? R.string.button_start_next
                            : R.string.button_start);
                } else {
                    startButton.setText(R.string.button_finish);
                }

                startButton.setVisibility(android.view.View.VISIBLE);
            }

            @Override
            public void onError(ApiResult<StatusResponse> error) {
                canStartGame = true;
                startButton.setEnabled(true);
                startButton.setText(R.string.button_start);
                startButton.setVisibility(android.view.View.VISIBLE);
            }
        });
    }
}
