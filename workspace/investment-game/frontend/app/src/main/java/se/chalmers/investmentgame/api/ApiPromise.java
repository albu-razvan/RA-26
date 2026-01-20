package se.chalmers.investmentgame.api;

public interface ApiPromise<T> {
    void onSuccess(T result);
    void onError(ApiResult<T> error);
}