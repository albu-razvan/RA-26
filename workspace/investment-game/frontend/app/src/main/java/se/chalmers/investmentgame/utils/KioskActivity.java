package se.chalmers.investmentgame.utils;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.os.Handler;
import android.view.MotionEvent;
import android.view.View;
import android.widget.Toast;

public class KioskActivity extends Activity {
    private static final String ACTION_EXIT_KIOSK = "se.chalmers.investmentgame.EXIT_KIOSK";
    private static final long EXIT_HOLD_DURATION = 10000; // 10 seconds
    private static boolean IS_TASK_IN_LOCK_MODE = false;

    private final Handler handler;

    private BroadcastReceiver exitReceiver;

    public KioskActivity() {
        super();

        this.handler = new Handler();
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        exitReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                if (ACTION_EXIT_KIOSK.equals(intent.getAction())) {
                    Toast.makeText(KioskActivity.this,
                            "Exiting kiosk mode...", Toast.LENGTH_SHORT).show();
                    stopLockTask();
                }
            }
        };

        super.onCreate(savedInstanceState);

        startLockTask();
        hideSystemUI();
        setupLongPressExit();
    }

    @SuppressLint("ClickableViewAccessibility")
    private void setupLongPressExit() {
        View rootView = getWindow().getDecorView().getRootView();
        Runnable exitRunnable = () -> {
            Toast.makeText(KioskActivity.this,
                    "Exiting kiosk mode...", Toast.LENGTH_SHORT).show();
            stopLockTask();
        };

        rootView.setOnTouchListener((view, event) -> {
            switch (event.getAction()) {
                case MotionEvent.ACTION_DOWN:
                    handler.postDelayed(exitRunnable, EXIT_HOLD_DURATION);

                    return true;

                case MotionEvent.ACTION_UP:
                case MotionEvent.ACTION_CANCEL:
                    handler.removeCallbacks(exitRunnable);

                    return true;
            }

            return false;
        });
    }

    @Override
    @SuppressLint({"UnspecifiedRegisterReceiverFlag"})
    protected void onResume() {
        super.onResume();

        registerReceiver(exitReceiver, new IntentFilter(ACTION_EXIT_KIOSK));
    }

    @Override
    protected void onPause() {
        super.onPause();

        unregisterReceiver(exitReceiver);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);

        if (hasFocus) {
            hideSystemUI();
        }
    }

    @Override
    public void startLockTask() {
        if (!IS_TASK_IN_LOCK_MODE) {
            // this should be called only once per task
            super.startLockTask();

            IS_TASK_IN_LOCK_MODE = true;
        }
    }

    @Override
    public void stopLockTask() {
        super.stopLockTask();

        IS_TASK_IN_LOCK_MODE = false;
    }

    @Override
    public void onBackPressed() {
        if (isBackPressEnabled()) {
            super.onBackPressed();
        }
    }

    protected boolean isBackPressEnabled() {
        return false;
    }

    private void hideSystemUI() {
        View decorView = getWindow().getDecorView();
        decorView.setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_FULLSCREEN);
    }
}
