package se.chalmers.investment.game.game;

import android.content.Intent;
import android.graphics.Typeface;
import android.os.Bundle;
import android.text.SpannableString;
import android.text.style.StyleSpan;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;

import androidx.annotation.Nullable;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import se.chalmers.investment.game.R;
import se.chalmers.investment.game.api.types.Game;
import se.chalmers.investment.game.api.types.StartGameResponse;
import se.chalmers.investment.game.utils.KioskActivity;
import se.chalmers.investment.game.views.InvestmentProgressView;

public class GameActivity extends KioskActivity {
    public static final String GAME_INTENT_KEY = "StartGameResponse";

    private InvestmentProgressView investmentVisualization;
    private View investmentOptions;
    private Button nextRound;
    private TextView budget;
    private TextView round;
    private TextView bank;
    private TextView summaryText;

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
        investmentOptions = findViewById(R.id.investment_options);
        RecyclerView recycler = findViewById(R.id.recycler);
        nextRound = findViewById(R.id.next);
        budget = findViewById(R.id.budget);
        round = findViewById(R.id.round);
        bank = findViewById(R.id.bank);
        summaryText = findViewById(R.id.summary_text);

        Game game = new Game(startGameResponse, this::update);
        update(game);

        recycler.setLayoutManager(new LinearLayoutManager(this,
                LinearLayoutManager.HORIZONTAL, false));
        recycler.setAdapter(new GameRecyclerAdapter(this, game));

        nextRound.setOnClickListener(view -> {
            investmentOptions.setVisibility(View.VISIBLE);
            nextRound.setVisibility(View.INVISIBLE);
            investmentVisualization.setVisibility(View.INVISIBLE);
            summaryText.setVisibility(View.INVISIBLE);

            round.setText("ROUND " + (game.getRound() + 1));
        });
    }

    private void update(Game game) {
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
            investmentVisualization.setRoundValues(-1, -1);
        } else {
            investmentVisualization.setCurrentProgress(getProgress(game, invVal, retVal));
            investmentVisualization.setRoundValues(invVal, retVal);
        }

        if (game.getRound() == 0) {
            investmentOptions.setVisibility(View.VISIBLE);
            nextRound.setVisibility(View.INVISIBLE);
            investmentVisualization.setVisibility(View.INVISIBLE);
            summaryText.setVisibility(View.INVISIBLE);

            round.setText("ROUND " + (game.getRound() + 1));
        } else {
            investmentOptions.setVisibility(View.INVISIBLE);
            investmentVisualization.setVisibility(View.VISIBLE);

            int roundNum = game.getRound();
            int invested = game.getInvested();
            int returned = game.getReturned();
            int uninvested = game.getRoundBudget() - invested;
            int totalThisRound = uninvested + returned;

            String rStr = String.valueOf(roundNum);
            String iStr = String.valueOf(invested);
            String reStr = String.valueOf(returned);
            String tStr = String.valueOf(totalThisRound);
            String uStr = String.valueOf(uninvested);

            String line1 = "In round " + rStr + ", you invested " + iStr
                    + " and received " + reStr + ".";
            String line2 = "Your total earnings this round were " + tStr + ".";
            String line3 = "(" + uStr + " unspent budget + " + reStr
                    + " investment return)";
            String text = line1 + "\n" + line2 + "\n" + line3;

            SpannableString string = new SpannableString(text);
            int start, end;

            start = ("In round " + rStr + ", you ").length();
            end = start + "invested ".length() + iStr.length();
            string.setSpan(new StyleSpan(Typeface.BOLD), start, end, 0);

            start = ("In round " + rStr + ", you invested " + iStr + " and ").length();
            end = start + "received ".length() + reStr.length();
            string.setSpan(new StyleSpan(Typeface.BOLD), start, end, 0);

            start = line1.length() + 1 + "Your ".length();
            end = start + "total".length();
            string.setSpan(new StyleSpan(Typeface.BOLD), start, end, 0);

            start = line1.length() + 1 + "Your total earnings this round were ".length();
            end = start + tStr.length();
            string.setSpan(new StyleSpan(Typeface.BOLD), start, end, 0);

            start = line1.length() + 1 + line2.length() + 1 + "(".length();
            end = start + uStr.length();
            string.setSpan(new StyleSpan(Typeface.BOLD), start, end, 0);

            start = line1.length() + 1 + line2.length() + 1 + "(".length() + uStr.length() + " unspent budget + ".length();
            end = start + reStr.length();
            string.setSpan(new StyleSpan(Typeface.BOLD), start, end, 0);

            summaryText.setText(string);
            summaryText.setVisibility(View.VISIBLE);

            if (game.getRoundsRemaining() <= 0) {
                nextRound.setText("End Game");
                nextRound.setOnClickListener(view -> {
                    Intent intent = new Intent(GameActivity.this, GameOverActivity.class);
                    intent.putExtra(GameOverActivity.BANK_INTENT_KEY, game.getBank());

                    startActivity(intent);
                    finishAfterTransition();
                });
            }

            nextRound.setVisibility(View.VISIBLE);
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
