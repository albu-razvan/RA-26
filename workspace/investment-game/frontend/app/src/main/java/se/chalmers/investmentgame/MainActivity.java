package se.chalmers.investmentgame;

import android.app.Activity;
import android.os.Bundle;
import android.util.Log;

import org.json.JSONException;
import org.json.JSONObject;

import se.chalmers.investmentgame.api.ApiPromise;
import se.chalmers.investmentgame.api.ApiRequest;
import se.chalmers.investmentgame.api.ApiResult;
import se.chalmers.investmentgame.api.types.InvestResponse;
import se.chalmers.investmentgame.api.types.StartGameResponse;

public class MainActivity extends Activity {
    private static final String TAG = "MainActivity";
    private static final String API = "http://192.168.0.102:8000";

    private String playerId;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(R.layout.activity_main);

        findViewById(R.id.start).setOnClickListener(view ->
                ApiRequest.post(API + "/start-game", StartGameResponse.class,
                        new ApiPromise<StartGameResponse>() {
                            @Override
                            public void onSuccess(StartGameResponse result) {
                                playerId = result.getPlayerId();

                                Log.i(TAG, "/start-game onSuccess: " + playerId);
                                Log.i(TAG, "/start-game onSuccess: " + result.getBank());
                                Log.i(TAG, "/start-game onSuccess: " + result.getMaxRounds());
                            }

                            @Override
                            public void onError(ApiResult<StartGameResponse> error) {
                                Log.e(TAG, "/start-game onError: " + error.error);
                            }
                        }));

        findViewById(R.id.invest).setOnClickListener(view -> {
            try {
                JSONObject object = new JSONObject();

                object.put("player_id", playerId);
                object.put("investment", 3);

                ApiRequest.post(API + "/invest", object,
                        InvestResponse.class, new ApiPromise<InvestResponse>() {
                            @Override
                            public void onSuccess(InvestResponse result) {
                                Log.i(TAG, "/invest onSuccess: " + result.getInvested());
                                Log.i(TAG, "/invest onSuccess: " + result.getReturned());
                                Log.i(TAG, "/invest onSuccess: " + result.getBank());
                                Log.i(TAG, "/invest onSuccess: " + result.getRound());
                                Log.i(TAG, "/invest onSuccess: " + result.getRoundsRemaining());
                            }

                            @Override
                            public void onError(ApiResult<InvestResponse> error) {
                                Log.e(TAG, "/invest onError: " + error.error);
                            }
                        });
            } catch (JSONException exception) {
                Log.e(TAG, "onCreate: ", exception);
            }
        });
    }
}