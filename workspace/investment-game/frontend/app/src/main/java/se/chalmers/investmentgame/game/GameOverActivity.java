package se.chalmers.investmentgame.game;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;

import androidx.annotation.Nullable;

import se.chalmers.investmentgame.R;

public class GameOverActivity extends Activity {
    public static final String BANK_INTENT_KEY = "BankGameValue";

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(R.layout.activity_game_over);

        ((TextView) findViewById(R.id.bank)).setText(String.valueOf(getIntent()
                .getIntExtra(BANK_INTENT_KEY, 0)));
    }
}
