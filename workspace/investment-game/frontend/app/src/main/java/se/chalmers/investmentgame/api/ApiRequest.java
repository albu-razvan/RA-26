package se.chalmers.investmentgame.api;

import android.util.Log;

import androidx.annotation.NonNull;

import com.google.gson.Gson;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

import se.chalmers.investmentgame.utils.Handlers;

public class ApiRequest {
    private static final String TAG = "ApiRequest";
    private static final String API = "http://192.168.0.102:8000";
    private static final Gson GSON = new Gson();

    public static <T> void get(String url, Class<T> clazz,
                               @NonNull ApiPromise<T> promise) {
        Handlers.EXECUTOR.execute(() -> {
            ApiResult<T> result = request(url, Method.GET, null, clazz);

            Handlers.MAIN_HANDLER.post(() -> {
                if (result.data != null) {
                    promise.onSuccess(result.data);
                } else {
                    promise.onError(result);
                }
            });
        });
    }

    public static <T> void post(String url, Class<T> clazz,
                                @NonNull ApiPromise<T> promise) {
        Handlers.EXECUTOR.execute(() -> {
            ApiResult<T> result = request(url, Method.POST, null, clazz);

            Handlers.MAIN_HANDLER.post(() -> {
                if (result.data != null) {
                    promise.onSuccess(result.data);
                } else {
                    promise.onError(result);
                }
            });
        });
    }

    public static <T> void post(String url, JSONObject body,
                                Class<T> clazz, @NonNull ApiPromise<T> promise) {
        Handlers.EXECUTOR.execute(() -> {
            ApiResult<T> result = request(url, Method.POST, body, clazz);

            Handlers.MAIN_HANDLER.post(() -> {
                if (result.data != null) {
                    promise.onSuccess(result.data);
                } else {
                    promise.onError(result);
                }
            });
        });
    }

    private static <T> ApiResult<T> request(String urlString,
                                            Method method, JSONObject body, Class<T> responseClass) {
        HttpURLConnection connection = null;
        BufferedReader reader = null;

        try {
            URL url = new URL(API + urlString);
            connection = (HttpURLConnection) url.openConnection();

            connection.setRequestMethod(method.name());
            connection.setConnectTimeout(10000);
            connection.setReadTimeout(10000);
            connection.setRequestProperty("Accept", "application/json");

            if (body != null) {
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type",
                        "application/json; charset=UTF-8");

                try (OutputStream outputStream = connection.getOutputStream()) {
                    outputStream.write(body.toString().getBytes(StandardCharsets.UTF_8));
                }
            }

            int statusCode = connection.getResponseCode();
            InputStream stream = (statusCode >= 200 && statusCode < 300)
                    ? connection.getInputStream()
                    : connection.getErrorStream();

            reader = new BufferedReader(new InputStreamReader(stream));
            StringBuilder response = new StringBuilder();
            String line;

            while ((line = reader.readLine()) != null) {
                response.append(line);
            }

            if (statusCode >= 200 && statusCode < 300) {
                T data = GSON.fromJson(response.toString(), responseClass);

                return ApiResult.success(data, statusCode);
            } else {
                return ApiResult.error(response.toString(), statusCode);
            }

        } catch (Exception exception) {
            Log.e(TAG, "Request failed", exception);

            return ApiResult.error(exception.getMessage(), -1);
        } finally {
            try {
                if (reader != null) {
                    reader.close();
                }
            } catch (Exception ignored) {
                Log.e(TAG, "Failed to close reader");
            }

            if (connection != null) {
                connection.disconnect();
            }
        }
    }
}
