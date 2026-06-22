package se.chalmers.investment.game.api;

public interface ApiPromise<T> {
    void onSuccess(T result);
    void onError(ApiResult<T> error);
}