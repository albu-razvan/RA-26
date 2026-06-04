package se.chalmers.investmentgame.api.types;

import com.google.gson.annotations.SerializedName;

public class ConfigureParticipantResponse {
    @SerializedName("status")
    private String status;

    @SerializedName("participant_id")
    private String participantId;

    public String getStatus() {
        return status;
    }

    public String getParticipantId() {
        return participantId;
    }
}
