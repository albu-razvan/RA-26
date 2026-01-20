package se.chalmers.investmentgame.api;

public class ApiResult<T> {
    public final T data;
    public final int code;
    public final String error;

    private ApiResult(T data, int code, String error) {
        this.data = data;
        this.code = code;
        this.error = error;
    }

    public static <T> ApiResult<T> success(T data, int code) {
        return new ApiResult<>(data, code, null);
    }

    public static <T> ApiResult<T> error(String error, int code) {
        return new ApiResult<>(null, code, error);
    }
}