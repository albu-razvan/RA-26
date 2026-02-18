package se.chalmers.investmentgame;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Toast;

import se.chalmers.investmentgame.api.ApiPromise;
import se.chalmers.investmentgame.api.ApiRequest;
import se.chalmers.investmentgame.api.ApiResult;
import se.chalmers.investmentgame.api.types.StartGameResponse;
import se.chalmers.investmentgame.game.GameActivity;
import se.chalmers.investmentgame.utils.KioskActivity;

public class MainActivity extends KioskActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(R.layout.activity_main);

        findViewById(R.id.start).setOnClickListener(view ->
                ApiRequest.post("/start-game", StartGameResponse.class,
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
                            }
                        }));
    }
}