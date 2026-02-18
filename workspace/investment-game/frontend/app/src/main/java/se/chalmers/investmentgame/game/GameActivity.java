package se.chalmers.investmentgame.game;

import android.content.Intent;
import android.os.Bundle;
import android.widget.TextView;

import androidx.annotation.Nullable;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import se.chalmers.investmentgame.R;
import se.chalmers.investmentgame.api.types.Game;
import se.chalmers.investmentgame.api.types.StartGameResponse;
import se.chalmers.investmentgame.utils.KioskActivity;
import se.chalmers.investmentgame.views.InvestmentProgressView;

public class GameActivity extends KioskActivity {
    public static final String GAME_INTENT_KEY = "StartGameResponse";

    private InvestmentProgressView investmentVisualization;
    private TextView invested;
    private TextView returned;
    private TextView budget;
    private TextView bank;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        StartGameResponse startGameResponse = getIntent().getParcelableExtra(GAME_INTENT_KEY);
        if (startGameResponse == null) {
            finish();

            return;
        }

        setContentView(R.layout.activity_game);

        investmentVisualization = findViewById(R.id.investment_visualization);
        RecyclerView recycler = findViewById(R.id.recycler);
        invested = findViewById(R.id.invested);
        returned = findViewById(R.id.returned);
        budget = findViewById(R.id.budget);
        bank = findViewById(R.id.bank);

        Game game = new Game(startGameResponse, this::update);
        update(game);

        recycler.setLayoutManager(new LinearLayoutManager(this,
                LinearLayoutManager.HORIZONTAL, false));
        recycler.setAdapter(new GameRecyclerAdapter(this, game));
    }

    private void update(Game game) {
        if (game.getRoundsRemaining() <= 0) {
            Intent intent = new Intent(this, GameOverActivity.class);
            intent.putExtra(GameOverActivity.BANK_INTENT_KEY, game.getBank());

            startActivity(intent);
            finishAfterTransition();
        } else {
            bank.animate().scaleX(1.2f)
                    .scaleY(1.2f)
                    .setDuration(100)
                    .withEndAction(() -> {
                        bank.setText(String.valueOf(game.getBank()));
                        bank.animate()
                                .scaleX(1.0f)
                                .scaleY(1.0f)
                                .setDuration(300);
                    });

            budget.setText(String.valueOf(game.getRoundBudget()));
            int invVal = game.getInvested();
            int retVal = game.getReturned();

            if (invVal == -1 || retVal == -1) {
                investmentVisualization.setCurrentProgress(0f);
                returned.setText("");
                invested.setText("");
            } else {
                investmentVisualization.setCurrentProgress(getProgress(game, invVal, retVal));
                invested.setText("Invested: " + invVal);
                returned.setText("Returned: " + retVal);
            }
        }
    }

    private float getProgress(Game game, int invested, int returned) {
        if (invested <= 0) {
            return 0f;
        }

        float gain = returned - invested;
        float maxGain = game.getMaxReturned() - invested;
        float maxLoss = invested - game.getMinReturned();

        if (gain >= 0 && maxGain > 0) {
            return gain / maxGain;
        }

        if (gain < 0 && maxLoss > 0) {
            return gain / maxLoss;
        }

        return 0f;
    }
}