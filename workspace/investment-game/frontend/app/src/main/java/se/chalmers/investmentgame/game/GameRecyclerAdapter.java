package se.chalmers.investmentgame.game;

import android.annotation.SuppressLint;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

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
    private static final String TAG = "GameRecyclerAdapter";

    private final LayoutInflater inflater;
    private final Game game;

    private int maxInvestment;

    GameRecyclerAdapter(LayoutInflater inflater, @NonNull Game game) {
        this.maxInvestment = game.getRoundBudget();
        this.inflater = inflater;
        this.game = game;
    }

    public static class ViewHolder extends RecyclerView.ViewHolder {
        private final TextView textView;

        public ViewHolder(@NonNull View itemView) {
            super(itemView);

            textView = itemView.findViewById(R.id.amount);
        }
    }

    @SuppressLint("InflateParams")
    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        return new ViewHolder(inflater.inflate(R.layout.investment_view_holder,
                null, false));
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        holder.textView.setText(String.valueOf(position));
        holder.itemView.setOnClickListener(view -> {
            try {
                JSONObject object = new JSONObject();

                object.put("player_id", game.getPlayerId());
                object.put("investment", holder.getAbsoluteAdapterPosition());

                ApiRequest.post("/invest", object,
                        InvestResponse.class, new ApiPromise<InvestResponse>() {
                            @Override
                            @SuppressLint("NotifyDataSetChanged")
                            public void onSuccess(InvestResponse result) {
                                game.update(result);

                                int newMaxInvestment = game.getRoundBudget();
                                if (newMaxInvestment != maxInvestment) {
                                    maxInvestment = game.getRoundBudget();
                                    notifyDataSetChanged();
                                }
                            }

                            @Override
                            public void onError(ApiResult<InvestResponse> error) {
                                Log.e(TAG, "/invest onError: " + error.error);
                            }
                        });
            } catch (JSONException exception) {
                Log.e(TAG, "onClick: ", exception);
            }
        });
    }

    @Override
    public int getItemCount() {
        return Math.max(0, maxInvestment + 1);
    }
}
