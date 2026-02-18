package se.chalmers.investmentgame.game;

import android.os.Bundle;
import android.widget.TextView;

import androidx.annotation.Nullable;

import se.chalmers.investmentgame.R;
import se.chalmers.investmentgame.utils.KioskActivity;

public class GameOverActivity extends KioskActivity {
    public static final String BANK_INTENT_KEY = "BankGameValue";

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(R.layout.activity_game_over);

        ((TextView) findViewById(R.id.bank)).setText(String.valueOf(getIntent()
                .getIntExtra(BANK_INTENT_KEY, 0)));
    }

    @Override
    protected boolean isBackPressEnabled() {
        return true;
    }
}
