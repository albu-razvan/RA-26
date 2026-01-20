package se.chalmers.investmentgame.game;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;

import androidx.annotation.Nullable;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import se.chalmers.investmentgame.R;
import se.chalmers.investmentgame.api.types.Game;
import se.chalmers.investmentgame.api.types.StartGameResponse;
import se.chalmers.investmentgame.views.InvestmentProgressView;

public class GameActivity extends Activity {
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
        recycler.setAdapter(new GameRecyclerAdapter(getLayoutInflater(), game));
    }

    private void update(Game game) {
        if (game.getRoundsRemaining() <= 0) {
            Intent intent = new Intent(this, GameOverActivity.class);
            intent.putExtra(GameOverActivity.BANK_INTENT_KEY, game.getBank());

            startActivity(intent);
            finishAfterTransition();
        } else {
            bank.setText(String.valueOf(game.getBank()));
            budget.setText(String.valueOf(game.getRoundBudget()));

            int invested = game.getInvested();
            int returned = game.getReturned();

            investmentVisualization.setCurrentProgress(getProgress(game, invested, returned));

            this.returned.setText(String.valueOf(returned));
            this.invested.setText(String.valueOf(invested));
        }
    }

    private float getProgress(Game game, int invested, int returned) {
        int minReturn = game.getMinReturned();
        int maxReturn = game.getMaxReturned();

        float progress;

        if (invested <= 0) {
            progress = 0f;
        } else {
            float gain = returned - invested;

            float maxGain = maxReturn - invested;
            float maxLoss = invested - minReturn;

            if (gain >= 0 && maxGain > 0) {
                progress = gain / maxGain;
            } else if (gain < 0 && maxLoss > 0) {
                progress = gain / maxLoss;
            } else {
                progress = 0f;
            }
        }

        return progress;
    }
}
