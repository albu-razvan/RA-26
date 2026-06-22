package se.chalmers.investmentgame.views;

import android.annotation.SuppressLint;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.util.AttributeSet;
import android.util.TypedValue;
import android.view.View;

import androidx.annotation.FloatRange;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

public class InvestmentProgressView extends View {
    private final int COLOR_GAIN = Color.parseColor("#0077B6");
    private final int COLOR_LOSS = Color.parseColor("#0077B6");
    private final int COLOR_BG = Color.parseColor("#F0F0F0");
    private final int COLOR_BORDER = Color.parseColor("#E4E4E7");
    private final int COLOR_DIVIDER = Color.parseColor("#BEBEC2");
    private final int COLOR_BUBBLE_BG = Color.parseColor("#FFFFFF");
    private final int COLOR_BUBBLE_STROKE = Color.parseColor("#D4D4D8");

    private Paint paint, backgroundPaint, glossPaint, borderPaint;
    private Paint labelPaint, valuePaint, bubblePaint, bubbleBorderPaint;
    private float currentProgress = 0;
    private int investedAmount = -1;
    private int returnedAmount = -1;

    public InvestmentProgressView(Context context, @Nullable AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    private void init() {
        paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        backgroundPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        backgroundPaint.setColor(COLOR_BG);

        borderPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        borderPaint.setStyle(Paint.Style.STROKE);
        borderPaint.setStrokeWidth(2f);
        borderPaint.setColor(COLOR_BORDER);

        glossPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        glossPaint.setColor(Color.WHITE);
        glossPaint.setAlpha(24);

        labelPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        labelPaint.setColor(Color.parseColor("#737373"));
        labelPaint.setTextAlign(Paint.Align.CENTER);
        labelPaint.setTextSize(sp(10));

        valuePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        valuePaint.setColor(Color.parseColor("#111111"));
        valuePaint.setFakeBoldText(true);
        valuePaint.setTextAlign(Paint.Align.CENTER);
        valuePaint.setTextSize(sp(14));

        bubblePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        bubblePaint.setStyle(Paint.Style.FILL);
        bubblePaint.setColor(COLOR_BUBBLE_BG);

        bubbleBorderPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        bubbleBorderPaint.setStyle(Paint.Style.STROKE);
        bubbleBorderPaint.setStrokeWidth(dp(1));
        bubbleBorderPaint.setColor(COLOR_BUBBLE_STROKE);
    }

    public void setCurrentProgress(@FloatRange(from = -1, to = 1) float progress) {
        this.currentProgress = Math.max(-1f, Math.min(1f, progress));

        invalidate();
    }

    public void setRoundValues(int invested, int returned) {
        investedAmount = invested;
        returnedAmount = returned;
        invalidate();
    }

    @Override
    @SuppressLint("DrawAllocation")
    protected void onDraw(@NonNull Canvas canvas) {
        super.onDraw(canvas);
        float width = getWidth(), height = getHeight();
        float centerX = width / 2f;
        float horizontalPadding = dp(8);

        boolean hasRoundValues = investedAmount >= 0 && returnedAmount >= 0;

        float labelY = dp(14);
        float barHeight = dp(20);
        float barTop = hasRoundValues ? dp(30) : (height - barHeight) / 2f;
        float maxBarTop = height - barHeight - dp(6);
        barTop = Math.min(barTop, maxBarTop);
        float barBottom = barTop + barHeight;
        float centerY = barTop + (barHeight / 2f);
        float radius = barHeight / 2f;

        // Track
        RectF bgRect = new RectF(horizontalPadding, barTop, width - horizontalPadding, barBottom);
        canvas.drawRoundRect(bgRect, radius, radius, backgroundPaint);
        canvas.drawRoundRect(bgRect, radius, radius, borderPaint);

        float left = centerX;
        float right = centerX;
        if (currentProgress != 0) {
            paint.setColor(currentProgress > 0 ? COLOR_GAIN : COLOR_LOSS);

            float progressWidth = ((width - (2f * horizontalPadding)) / 2f) * Math.abs(currentProgress);
            left = currentProgress > 0 ? centerX : centerX - progressWidth;
            right = currentProgress > 0 ? centerX + progressWidth : centerX;

            RectF progressRect = new RectF(left, barTop, right, barBottom);

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
        paint.setColor(COLOR_DIVIDER);
        paint.setAlpha(255);
        canvas.drawRect(centerX - 1.5f, barTop, centerX + 1.5f, barBottom, paint);

        if (hasRoundValues) {
            drawRoundText(canvas, centerX, left, right, width, horizontalPadding, labelY, centerY);
        }
    }

    private void drawRoundText(
            Canvas canvas,
            float centerX,
            float progressLeft,
            float progressRight,
            float width,
            float horizontalPadding,
            float labelY,
            float centerY
    ) {
        String investedLabel = "Invested";
        String investedValue = String.valueOf(investedAmount);
        String returnedLabel = "Returned";
        String returnedValue = String.valueOf(returnedAmount);
        float bubbleRadius = dp(12);

        float investedX = centerX;
        float returnedX;
        if (currentProgress > 0f) {
            returnedX = progressRight;
        } else if (currentProgress < 0f) {
            returnedX = progressLeft;
        } else {
            returnedX = centerX;
        }

        float minBubbleX = horizontalPadding + bubbleRadius;
        float maxBubbleX = width - horizontalPadding - bubbleRadius;
        returnedX = clamp(returnedX, minBubbleX, maxBubbleX);

        float requiredBubbleGap = (bubbleRadius * 2f) + dp(6);
        float bubbleGap = Math.abs(returnedX - investedX);
        if (bubbleGap < requiredBubbleGap) {
            if (currentProgress >= 0f) {
                returnedX = investedX + requiredBubbleGap;
            } else {
                returnedX = investedX - requiredBubbleGap;
            }
            returnedX = clamp(returnedX, minBubbleX, maxBubbleX);

            bubbleGap = Math.abs(returnedX - investedX);
            if (bubbleGap < requiredBubbleGap) {
                float correction = (requiredBubbleGap - bubbleGap) / 2f;
                if (currentProgress >= 0f) {
                    investedX -= correction;
                    returnedX += correction;
                } else {
                    investedX += correction;
                    returnedX -= correction;
                }
                investedX = clamp(investedX, minBubbleX, maxBubbleX);
                returnedX = clamp(returnedX, minBubbleX, maxBubbleX);
            }
        }

        float investedLabelHalf = labelPaint.measureText(investedLabel) / 2f;
        float returnedLabelHalf = labelPaint.measureText(returnedLabel) / 2f;

        float investedLabelX = clamp(investedX, horizontalPadding + investedLabelHalf, width - horizontalPadding - investedLabelHalf);
        float returnedLabelX = clamp(returnedX, horizontalPadding + returnedLabelHalf, width - horizontalPadding - returnedLabelHalf);

        float requiredLabelGap = investedLabelHalf + returnedLabelHalf + dp(6);
        float labelGap = Math.abs(returnedLabelX - investedLabelX);
        if (labelGap < requiredLabelGap) {
            float correction = (requiredLabelGap - labelGap) / 2f;
            if (currentProgress >= 0f) {
                investedLabelX -= correction;
                returnedLabelX += correction;
            } else {
                investedLabelX += correction;
                returnedLabelX -= correction;
            }

            investedLabelX = clamp(investedLabelX, horizontalPadding + investedLabelHalf, width - horizontalPadding - investedLabelHalf);
            returnedLabelX = clamp(returnedLabelX, horizontalPadding + returnedLabelHalf, width - horizontalPadding - returnedLabelHalf);
        }

        canvas.drawText(investedLabel, investedLabelX, labelY, labelPaint);
        canvas.drawText(returnedLabel, returnedLabelX, labelY, labelPaint);

        drawValueBubble(canvas, investedX, centerY, bubbleRadius, investedValue);
        drawValueBubble(canvas, returnedX, centerY, bubbleRadius, returnedValue);
    }

    private void drawValueBubble(Canvas canvas, float x, float y, float radius, String value) {
        canvas.drawCircle(x, y, radius, bubblePaint);
        canvas.drawCircle(x, y, radius, bubbleBorderPaint);

        Paint.FontMetrics metrics = valuePaint.getFontMetrics();
        float textBaseline = y - ((metrics.ascent + metrics.descent) / 2f);
        canvas.drawText(value, x, textBaseline, valuePaint);
    }

    private float clamp(float value, float min, float max) {
        return Math.max(min, Math.min(max, value));
    }

    private float dp(float value) {
        return TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, value, getResources().getDisplayMetrics());
    }

    private float sp(float value) {
        return TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, value, getResources().getDisplayMetrics());
    }
}
