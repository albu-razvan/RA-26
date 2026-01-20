package se.chalmers.investmentgame.views;

import android.annotation.SuppressLint;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.util.AttributeSet;
import android.view.View;

import androidx.annotation.FloatRange;
import androidx.annotation.IntRange;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

public class InvestmentProgressView extends View {
    private final int COLOR_GAIN = Color.parseColor("#4CAF50");
    private final int COLOR_LOSS = Color.parseColor("#F44336");
    private final int COLOR_BG = Color.parseColor("#E0E0E0");

    private Paint paint;
    private Paint backgroundPaint;
    private float currentProgress;

    public InvestmentProgressView(Context context, @Nullable AttributeSet attrs) {
        super(context, attrs);

        init();
    }

    private void init() {
        paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        backgroundPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        backgroundPaint.setColor(COLOR_BG);

        currentProgress = 0;
    }

    public void setCurrentProgress(@FloatRange(from = -1, to = 1) float progress) {
        this.currentProgress = Math.max(-1f, Math.min(1f, progress));

        invalidate();
    }

    @Override
    @SuppressLint("DrawAllocation")
    protected void onDraw(@NonNull Canvas canvas) {
        super.onDraw(canvas);

        float width = getWidth();
        float height = getHeight();
        float centerX = width / 2f;
        float centerY = height / 2f;
        float barHeight = height * 0.5f;
        float cornerRadius = 15f;

        RectF bgRect = new RectF(0, centerY - barHeight / 2,
                width, centerY + barHeight / 2);
        canvas.drawRoundRect(bgRect, cornerRadius, cornerRadius, backgroundPaint);

        if (currentProgress != 0) {
            boolean isGain = currentProgress > 0;
            paint.setColor(isGain ? COLOR_GAIN : COLOR_LOSS);

            float left, right;
            if (isGain) {
                left = centerX;
                right = centerX + (centerX * currentProgress);
            } else {
                left = centerX + (centerX * currentProgress);
                right = centerX;
            }

            RectF progressRect = new RectF(left, centerY - barHeight / 2,
                    right, centerY + barHeight / 2);
            canvas.drawRect(progressRect, paint);
        }

        paint.setColor(Color.GRAY);
        canvas.drawRect(centerX - 2, centerY - (barHeight * 0.7f) / 2, centerX + 2,
                centerY + (barHeight * 0.7f) / 2, paint);
    }
}