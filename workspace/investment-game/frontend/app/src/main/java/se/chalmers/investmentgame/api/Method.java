package se.chalmers.investmentgame.api;

enum Method {
    GET("GET"),
    POST("POST");

    private final String method;

    Method(String method) {
        this.method = method;
    }

    @Override
    public String toString() {
        return method;
    }
}