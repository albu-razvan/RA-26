package se.chalmers.investmentgame.game;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Context;
import android.util.Log;
import android.view.HapticFeedbackConstants;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import org.json.JSONException;
import org.json.JSONObject;

import se.chalmers.investmentgame.R;
import se.chalmers.investmentgame.api.ApiPromise;
import se.chalmers.investmentgame.api.ApiRequest;
import se.chalmers.investmentgame.api.ApiResult;
import se.chalmers.investmentgame.api.types.Game;
import se.chalmers.investmentgame.api.types.InvestResponse;

public class GameRecyclerAdapter extends RecyclerView.Adapter<GameRecyclerAdapter.ViewHolder> {
    private static final String TAG = "Adapter";

    private final Activity activity;
    private final Game game;

    private int maxInvestment;

    GameRecyclerAdapter(Activity activity, @NonNull Game game) {
        this.maxInvestment = game.getRoundBudget();
        this.activity = activity;
        this.game = game;
    }

    public static class ViewHolder extends RecyclerView.ViewHolder {
        private final Button button;

        public ViewHolder(@NonNull View itemView) {
            super(itemView);
            button = itemView.findViewById(R.id.amount);
        }
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        return new ViewHolder(activity.getLayoutInflater()
                .inflate(R.layout.investment_view_holder, parent, false));
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        holder.button.setText(String.valueOf(position));
        holder.button.setOnClickListener(view -> {
            view.performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY);
            try {
                JSONObject object = new JSONObject();
                object.put("player_id", game.getPlayerId());
                object.put("investment", holder.getAbsoluteAdapterPosition());

                ApiRequest.post(activity, "/invest", object,
                        InvestResponse.class, new ApiPromise<InvestResponse>() {
                            @Override
                            @SuppressLint("NotifyDataSetChanged")
                            public void onSuccess(InvestResponse result) {
                                game.update(result);
                                if (game.getRoundBudget() != maxInvestment) {
                                    maxInvestment = game.getRoundBudget();
                                    notifyDataSetChanged();
                                }
                            }

                            @Override
                            public void onError(ApiResult<InvestResponse> error) {
                                Log.e(TAG, "Error: " + error.error);
                            }
                        });
            } catch (JSONException exception) {
                Log.e(TAG, "onBindViewHolder: ", exception);
            }
        });
    }

    @Override
    public int getItemCount() {
        return maxInvestment + 1;
    }
}