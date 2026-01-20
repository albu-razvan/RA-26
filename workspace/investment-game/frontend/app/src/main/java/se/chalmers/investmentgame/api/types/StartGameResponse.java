package se.chalmers.investmentgame.api.types;

import com.google.gson.annotations.SerializedName;

public class StartGameResponse {
    @SerializedName("player_id")
    private String playerId;

    @SerializedName("bank")
    private int bank;

    @SerializedName("max_rounds")
    private int maxRounds;

    public StartGameResponse() {
    }

    public String getPlayerId() {
        return playerId;
    }

    public int getBank() {
        return bank;
    }

    public int getMaxRounds() {
        return maxRounds;
    }
}
