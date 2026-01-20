package se.chalmers.investmentgame.api.types;

import com.google.gson.annotations.SerializedName;

public class InvestResponse {
    @SerializedName("round")
    private int round;

    @SerializedName("invested")
    private int invested;

    @SerializedName("returned")
    private int returned;

    @SerializedName("min_returned")
    private int minReturned;

    @SerializedName("max_returned")
    private int maxReturned;

    @SerializedName("round_budget")
    private int roundBudget;

    @SerializedName("bank")
    private int bank;

    @SerializedName("rounds_remaining")
    private int roundsRemaining;

    public InvestResponse() {
    }

    public int getBank() {
        return bank;
    }

    public int getInvested() {
        return invested;
    }

    public int getMinReturned() {
        return minReturned;
    }

    public int getMaxReturned() {
        return maxReturned;
    }

    public int getReturned() {
        return returned;
    }

    public int getRound() {
        return round;
    }

    public int getRoundBudget() {
        return roundBudget;
    }

    public int getRoundsRemaining() {
        return roundsRemaining;
    }
}
