package se.chalmers.investmentgame;

import android.app.Activity;
import android.app.Application;
import android.app.Dialog;
import android.content.Context;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.Window;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.ProgressBar;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import java.util.concurrent.atomic.AtomicReference;

public class GameApplication extends Application {
    private static final Handler UI_HANDLER = new Handler(Looper.getMainLooper());

    private Activity currentActivity;

    /**
     * Returns a Runnable that will hide the dialog
     */
    public static Runnable showLoadingDialog(Context context) {
        GameApplication application = (GameApplication) context.getApplicationContext();

        if (application.currentActivity != null
                && !application.currentActivity.isFinishing()) {

            AtomicReference<Dialog> dialogHolder = new AtomicReference<>(null);

            UI_HANDLER.post(() -> {
                Activity activity = application.currentActivity;
                Dialog dialog = new Dialog(activity);
                Window window = dialog.getWindow();

                if (window != null) {
                    window.setBackgroundDrawableResource(android.R.color.transparent);
                    window.addFlags(WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE);
                    window.setDimAmount(0.8f);

                    int uiOptions = activity.getWindow().getDecorView().getSystemUiVisibility();
                    window.getDecorView().setSystemUiVisibility(uiOptions);

                    FrameLayout container = new FrameLayout(activity);
                    container.setLayoutParams(new FrameLayout.LayoutParams(
                            FrameLayout.LayoutParams.MATCH_PARENT,
                            FrameLayout.LayoutParams.MATCH_PARENT
                    ));

                    ProgressBar spinner = new ProgressBar(activity, null,
                            android.R.attr.progressBarStyleLarge);
                    spinner.getIndeterminateDrawable().setTint(Color.WHITE);

                    FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(
                            FrameLayout.LayoutParams.WRAP_CONTENT,
                            FrameLayout.LayoutParams.WRAP_CONTENT
                    );
                    params.gravity = Gravity.CENTER;

                    container.addView(spinner, params);

                    dialog.setContentView(container);
                    dialog.setCancelable(false);
                    dialog.show();

                    window.clearFlags(WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE);
                    dialogHolder.set(dialog);
                }
            });

            return () -> UI_HANDLER.post(() -> {
                Dialog dialog = dialogHolder.get();

                if (dialog != null && dialog.isShowing()) {
                    dialog.dismiss();
                }
            });
        }

        return null;
    }

    @Override
    public void onCreate() {
        super.onCreate();

        registerActivityLifecycleCallbacks(new ActivityLifecycleCallbacks() {
            @Override
            public void onActivityResumed(@NonNull Activity activity) {
                currentActivity = activity;
            }

            @Override
            public void onActivityPaused(@NonNull Activity activity) {
                currentActivity = null;
            }

            @Override
            public void onActivityCreated(@NonNull Activity activity, @Nullable Bundle bundle) {
            }

            @Override
            public void onActivityDestroyed(@NonNull Activity activity) {
            }

            @Override
            public void onActivitySaveInstanceState(@NonNull Activity activity, @NonNull Bundle bundle) {
            }

            @Override
            public void onActivityStarted(@NonNull Activity activity) {
            }

            @Override
            public void onActivityStopped(@NonNull Activity activity) {
            }
        });
    }
}
