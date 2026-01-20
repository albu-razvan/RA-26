package se.chalmers.investmentgame.api.types;

import android.os.Parcel;
import android.os.Parcelable;

import com.google.gson.annotations.SerializedName;

public class StartGameResponse implements Parcelable {
    @SerializedName("player_id")
    private String playerId;

    @SerializedName("bank")
    private int bank;

    @SerializedName("round_budget")
    private int roundBudget;

    @SerializedName("max_rounds")
    private int maxRounds;

    public StartGameResponse() {
    }

    protected StartGameResponse(Parcel in) {
        playerId = in.readString();
        bank = in.readInt();
        roundBudget = in.readInt();
        maxRounds = in.readInt();
    }

    public static final Creator<StartGameResponse> CREATOR = new Creator<StartGameResponse>() {
        @Override
        public StartGameResponse createFromParcel(Parcel in) {
            return new StartGameResponse(in);
        }

        @Override
        public StartGameResponse[] newArray(int size) {
            return new StartGameResponse[size];
        }
    };

    @Override
    public void writeToParcel(Parcel dest, int flags) {
        dest.writeString(playerId);
        dest.writeInt(bank);
        dest.writeInt(roundBudget);
        dest.writeInt(maxRounds);
    }

    @Override
    public int describeContents() {
        return 0;
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

    public int getRoundBudget() {
        return roundBudget;
    }
}
