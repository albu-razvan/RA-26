package se.chalmers.investmentgame.views;

import android.annotation.SuppressLint;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.util.AttributeSet;
import android.view.View;

import androidx.annotation.FloatRange;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

public class InvestmentProgressView extends View {
    private final int COLOR_GAIN = Color.parseColor("#66BB6A");
    private final int COLOR_LOSS = Color.parseColor("#EF5350");
    private final int COLOR_BG = Color.parseColor("#33000000");

    private Paint paint, backgroundPaint, glossPaint;
    private float currentProgress = 0;

    public InvestmentProgressView(Context context, @Nullable AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    private void init() {
        paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        backgroundPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        backgroundPaint.setColor(COLOR_BG);

        glossPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        glossPaint.setColor(Color.WHITE);
        glossPaint.setAlpha(40);
    }

    public void setCurrentProgress(@FloatRange(from = -1, to = 1) float progress) {
        this.currentProgress = Math.max(-1f, Math.min(1f, progress));

        invalidate();
    }

    @Override
    @SuppressLint("DrawAllocation")
    protected void onDraw(@NonNull Canvas canvas) {
        super.onDraw(canvas);
        float width = getWidth(), height = getHeight();
        float centerX = width / 2f, centerY = height / 2f;
        float barHeight = height * 0.6f, radius = barHeight / 2f;

        // Track
        RectF bgRect = new RectF(0, centerY - barHeight / 2, width, centerY + barHeight / 2);
        canvas.drawRoundRect(bgRect, radius, radius, backgroundPaint);

        if (currentProgress != 0) {
            paint.setColor(currentProgress > 0 ? COLOR_GAIN : COLOR_LOSS);

            float progressWidth = (width / 2f) * Math.abs(currentProgress);
            float left = currentProgress > 0 ? centerX : centerX - progressWidth;
            float right = currentProgress > 0 ? centerX + progressWidth : centerX;

            RectF progressRect = new RectF(left, centerY - barHeight / 2, right, centerY + barHeight / 2);

            float[] radii;
            if (currentProgress > 0) {
                radii = new float[]{0, 0, radius, radius, radius, radius, 0, 0};
            } else {
                radii = new float[]{radius, radius, 0, 0, 0, 0, radius, radius};
            }

            Path progressPath = new Path();
            progressPath.addRoundRect(progressRect, radii, Path.Direction.CW);
            canvas.drawPath(progressPath, paint);

            canvas.save();

            canvas.clipPath(progressPath);
            RectF glossRect = new RectF(left, progressRect.top, right, centerY - barHeight / 6);
            canvas.drawRect(glossRect, glossPaint);

            canvas.restore();
        }

        // Divider
        paint.setColor(Color.WHITE);
        paint.setAlpha(150);
        canvas.drawRect(centerX - 1.5f, centerY - (barHeight / 2),
                centerX + 1.5f, centerY + (barHeight / 2), paint);
    }
}