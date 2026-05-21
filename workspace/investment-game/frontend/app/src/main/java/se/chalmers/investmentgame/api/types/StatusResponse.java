package se.chalmers.investmentgame.api.types;

import com.google.gson.annotations.SerializedName;

public class StatusResponse {
    @SerializedName("state")
    private String state;

    @SerializedName("state_version")
    private int stateVersion;

    @SerializedName("games_played")
    private int gamesPlayed;

    @SerializedName("games_remaining")
    private int gamesRemaining;

    @SerializedName("game_limit")
    private int gameLimit;

    @SerializedName("has_next_game")
    private boolean hasNextGame;

    @SerializedName("participant_complete")
    private boolean participantComplete;

    public String getState() {
        return state;
    }

    public int getStateVersion() {
        return stateVersion;
    }

    public int getGamesPlayed() {
        return gamesPlayed;
    }

    public int getGamesRemaining() {
        return gamesRemaining;
    }

    public int getGameLimit() {
        return gameLimit;
    }

    public boolean hasNextGame() {
        return hasNextGame;
    }

    public boolean isParticipantComplete() {
        return participantComplete;
    }
}
