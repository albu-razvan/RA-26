package se.chalmers.investmentgame.api.types;

import com.google.gson.annotations.SerializedName;

public class InvestResponse {
    @SerializedName("round")
    private int round;

    @SerializedName("invested")
    private int invested;

    @SerializedName("returned")
    private int returned;

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

    public int getReturned() {
        return returned;
    }

    public int getRound() {
        return round;
    }

    public int getRoundsRemaining() {
        return roundsRemaining;
    }
}
