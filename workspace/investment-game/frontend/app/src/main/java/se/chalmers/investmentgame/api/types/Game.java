package se.chalmers.investmentgame.api.types;

import androidx.annotation.NonNull;

public class Game {
    private final UpdateListener listener;
    private final String playerId;
    private final int maxRounds;

    private int roundsRemaining;
    private int roundBudget;
    private int maxReturned;
    private int minReturned;
    private int invested;
    private int returned;
    private int round;
    private int bank;

    public Game(@NonNull StartGameResponse startGameResponse, @NonNull UpdateListener listener) {
        this.playerId = startGameResponse.getPlayerId();
        this.maxRounds = startGameResponse.getMaxRounds();
        this.roundBudget = startGameResponse.getRoundBudget();
        this.bank = startGameResponse.getBank();

        this.listener = listener;

        this.roundsRemaining = maxRounds;
        this.minReturned = 0;
        this.maxReturned = 0;
        this.invested = 0;
        this.returned = 0;
        this.round = 0;
    }

    public void update(@NonNull InvestResponse investResponse) {
        this.bank = investResponse.getBank();
        this.round = investResponse.getRound();
        this.invested = investResponse.getInvested();
        this.returned = investResponse.getReturned();
        this.roundBudget = investResponse.getRoundBudget();
        this.minReturned = investResponse.getMinReturned();
        this.maxReturned = investResponse.getMaxReturned();
        this.roundsRemaining = investResponse.getRoundsRemaining();

        listener.onUpdate(this);
    }

    public int getRoundsRemaining() {
        return roundsRemaining;
    }

    public int getRoundBudget() {
        return roundBudget;
    }

    public String getPlayerId() {
        return playerId;
    }

    public int getMaxRounds() {
        return maxRounds;
    }

    public int getReturned() {
        return returned;
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

    public int getRound() {
        return round;
    }

    public int getBank() {
        return bank;
    }

    public interface UpdateListener {
        void onUpdate(Game game);
    }
}
