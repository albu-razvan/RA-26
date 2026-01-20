package se.chalmers.investmentgame.utils;

import android.os.Handler;
import android.os.Looper;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class Handlers {
    public static final ExecutorService EXECUTOR = Executors.newSingleThreadExecutor();
    public static final Handler MAIN_HANDLER = new Handler(Looper.getMainLooper());
}
