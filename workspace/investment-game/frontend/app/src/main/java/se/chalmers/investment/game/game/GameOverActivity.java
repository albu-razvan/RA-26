package se.chalmers.investment.game.game;

import android.content.Intent;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.Nullable;

import se.chalmers.investment.game.R;
import se.chalmers.investment.game.api.ApiPromise;
import se.chalmers.investment.game.api.ApiRequest;
import se.chalmers.investment.game.api.ApiResult;
import se.chalmers.investment.game.api.types.StatusResponse;
import se.chalmers.investment.game.api.types.StartGameResponse;
import se.chalmers.investment.game.utils.KioskActivity;

public class GameOverActivity extends KioskActivity {
    public static final String BANK_INTENT_KEY = "BankGameValue";
    private static final String TAG = "GameOverActivity";

    private boolean resetRequested;
    private boolean statusLoaded;
    private boolean hasNextGame;
    private boolean launchingNextGame;

    private View postGameContainer;
    private TextView nextMessage;
    private TextView questionnaireMessage;
    private TextView finishButton;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(R.layout.activity_game_over);

        ((TextView) findViewById(R.id.bank)).setText(String.valueOf(getIntent()
                .getIntExtra(BANK_INTENT_KEY, 0)));

        postGameContainer = findViewById(R.id.post_game_container);
        nextMessage = findViewById(R.id.next_game_message);
        questionnaireMessage = findViewById(R.id.questionnaire_message);
        finishButton = findViewById(R.id.finish_game_over);

        finishButton.setOnClickListener(view -> {
            if (!statusLoaded) {
                return;
            }

            if (!hasNextGame) {
                return;
            }

            startNextGame();
        });
    }

    @Override
    protected void onResume() {
        super.onResume();

        if (!statusLoaded) {
            fetchStatusAndRender();
        }
    }

    private void fetchStatusAndRender() {
        ApiRequest.get(this, "/status", StatusResponse.class, new ApiPromise<StatusResponse>() {
            @Override
            public void onSuccess(StatusResponse status) {
                hasNextGame = status.getGamesRemaining() > 0;
                statusLoaded = true;

                if (hasNextGame) {
                    questionnaireMessage.setText(R.string.questionnaire_prompt);
                    nextMessage.setText(R.string.questionnaire_next_game);
                    nextMessage.setVisibility(View.VISIBLE);
                    finishButton.setText(R.string.button_start_next);
                    finishButton.setVisibility(View.VISIBLE);
                    finishButton.setEnabled(true);
                } else {
                    questionnaireMessage.setText(R.string.questionnaire_last_game);
                    nextMessage.setVisibility(View.GONE);
                    finishButton.setVisibility(View.GONE);
                    finishButton.setEnabled(false);
                }

                postGameContainer.setVisibility(View.VISIBLE);
            }

            @Override
            public void onError(ApiResult<StatusResponse> error) {
                hasNextGame = true;
                statusLoaded = true;

                questionnaireMessage.setText(R.string.questionnaire_prompt);
                nextMessage.setText(R.string.questionnaire_next_game);
                nextMessage.setVisibility(View.VISIBLE);
                finishButton.setText(R.string.button_start_next);
                finishButton.setVisibility(View.VISIBLE);
                finishButton.setEnabled(true);
                postGameContainer.setVisibility(View.VISIBLE);
            }
        });
    }

    private void startNextGame() {
        finishButton.setEnabled(false);

        ApiRequest.post(this, "/start-game", StartGameResponse.class,
                new ApiPromise<StartGameResponse>() {
                    @Override
                    public void onSuccess(StartGameResponse result) {
                        launchingNextGame = true;
                        resetRequested = true;

                        Intent intent = new Intent(GameOverActivity.this, GameActivity.class);
                        intent.putExtra(GameActivity.GAME_INTENT_KEY, result);
                        startActivity(intent);
                        finish();
                    }

                    @Override
                    public void onError(ApiResult<StartGameResponse> error) {
                        finishButton.setEnabled(true);
                        Toast.makeText(GameOverActivity.this,
                                error.error, Toast.LENGTH_LONG).show();
                    }
                });
    }

    @Override
    protected void onStop() {
        super.onStop();

        if (launchingNextGame) {
            return;
        }

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
