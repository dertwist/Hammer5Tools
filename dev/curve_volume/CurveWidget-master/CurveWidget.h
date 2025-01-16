#ifndef CURVEWIDGET_H
#define CURVEWIDGET_H

#include <assert.h>
#include <algorithm> // max

#include <QWidget>
#include <QtGui>
#include <QtCore>
#include <QVector2D>


struct Curve
{
	union
	{
		struct
		{
			QVector2D A;
			QVector2D B;
			QVector2D P1;
			QVector2D P2;
		};
		QVector2D dots[4] = {QVector2D(0.0f, 0.0f), QVector2D(1.0f, 1.0f), QVector2D(0.0f, 1.0f), QVector2D(1.0f, 0.0f)};
	};

	Curve(){}

	QVector2D Evaluate(float t)
	{
		return	1.0f * pow(t, 3.0f) * (B + 3.0f * (P1 - P2) - A) +
				3.0f * pow(t, 2.0f) * (A - 2.0f * P1 + P2) +
				3.0f * t * (P1 - A) +
				A;
	}
};


class CurveWidget : public QWidget
{
	Q_OBJECT

	// Number of pixels in one analytic unit
	float pixelsInUnitScale{100};

	// Offset analytic coordinate system relative to Top Left widget point in pixels
	QVector2D centerOffset;

	QPoint mousePosition;

	// Dragging data
	int isDragging{0}; // 1 - left, 2 - wheel
	QPoint dragStartMousePos;
	QVector2D dragStartPixelsOffset;
	int dragDotIdx = -1;

	int mouseUnderPoint[4] = {};

	std::unique_ptr<QTimer> timer;

	Curve currentCurve;

public:
	explicit CurveWidget(QWidget *parent = nullptr);

private slots:
	void showContextMenu(const QPoint &pos);
	void onTimer();

protected:
	void paintEvent(QPaintEvent *e) override;
	void mousePressEvent(QMouseEvent *event) override;
	void mouseReleaseEvent(QMouseEvent *event) override;
	void mouseMoveEvent(QMouseEvent *event) override;
	void wheelEvent(QWheelEvent *event) override;
	void resizeEvent(QResizeEvent *event) override;
	void showEvent(QShowEvent *event) override;
public:
	void SetCurve(const Curve& curve) { currentCurve = curve; }
	void NormalizeView();

private:

	// Analytic Coordinate System	- The coordinate system in which the coordinates of the curve are specified
	// Canvas Coordinate System		- Coordinates inside the widget. Top left - (0, 0)
	//
	QPoint ToCanvasCoordinates(const QVector2D& analyticPos);
	QVector2D ToAnalyticCoordinates(const QPoint& canvasPos);

	float GetAnalyticUnitInPixels() { return pixelsInUnitScale; }
	float GetPixelInAnalyticUnit() { return 1 / pixelsInUnitScale; }
};

#endif // CURVEWIDGET_H
