#include "CurveWidget.h"
#include <QDesktopWidget>
#include <QRect>
#include <QApplication>
#include <QMouseEvent>
#include <QWheelEvent>
#include <QMenu>
#include <QAction>

const int MinimumSelectDotsDistance = 9;
const QColor DotEdgeColor(0, 0, 0);
const QColor DotColor(255, 255, 255);
const QColor DotEdgeSelectionColor(255, 0, 0);
const QColor DotSelectionColor(255, 255, 255);
const QColor GridThinColor(46, 46, 46);
const int GridWidth = 1;
const int DotSize = 3;
const QColor FatGridColor(80, 80, 80);

inline float clamp(float n, float lower, float upper)
{
	return std::max(lower, std::min(n, upper));
}

/*float PointToSegmentDistance(const QPoint& a, const QPoint& b, const QPoint& p)
{
	QVector2D n = b - a;
	QVector2D pa = a - p;
	QVector2D c = n * (QVector2D::dotProduct( pa, n ) / QVector2D::dotProduct( n, n ));
	QVector2D d = pa - c;
	return sqrt( QVector2D::dotProduct( d, d ) );
}*/
CurveWidget::CurveWidget(QWidget *parent) : QWidget(parent)
{
	setMouseTracking(true);

	QPalette Pal(palette());
	Pal.setColor(QPalette::Background, QColor(38, 38, 38));
	setAutoFillBackground(true);
	setPalette(Pal);

	//this->setSizePolicy(QSizePolicy::Maximum, QSizePolicy::Maximum);

//	QDesktopWidget *desktop = QApplication::desktop();
//	QRect screenSize = desktop->availableGeometry(this);
//	//resize(QSize(float(screenSize.x()) * 0.8f, float(screenSize.y()) * 0.8f));
	//resize(200, 100);

	this->setContextMenuPolicy(Qt::CustomContextMenu);

	connect(this, SIGNAL(customContextMenuRequested(const QPoint &)), this, SLOT(showContextMenu(const QPoint &)));

	timer = std::make_unique<QTimer>(this);
	connect(timer.get(), SIGNAL(timeout()), this, SLOT(onTimer()));
	timer->start(16);
}

void CurveWidget::showContextMenu(const QPoint &pos)
{
   QMenu contextMenu(tr("Context menu"), this);

   QAction action1("Add Point", this);
   connect(&action1, SIGNAL(triggered()), this, SLOT(removeDataPoint()));
   contextMenu.addAction(&action1);

   QAction action2("Remove Point", this);
   connect(&action2, SIGNAL(triggered()), this, SLOT(removeDataPoint()));
   contextMenu.addAction(&action2);

   contextMenu.exec(mapToGlobal(pos));
}

void CurveWidget::onTimer()
{
	int isMouseUnderDot[4] = {};

	auto check_dot_intersection = [&](const QVector2D& P) -> int
	{
		auto dist = (mousePosition - ToCanvasCoordinates(P)).manhattanLength();
		return (dist < MinimumSelectDotsDistance);
	};

	for (int i = 0; i<4; i++)
		isMouseUnderDot[i] = check_dot_intersection(currentCurve.dots[i]);

	if (memcmp(isMouseUnderDot, mouseUnderPoint, sizeof(int) * 4))
	{
		memcpy(mouseUnderPoint, isMouseUnderDot, sizeof(int) * 4);
		repaint();
	}
}

void CurveWidget::paintEvent(QPaintEvent *e)
{
	Q_UNUSED(e)

	QPainter painter(this);
	painter.setRenderHint(QPainter::Antialiasing, false);
	painter.setPen(QPen(GridThinColor, GridWidth, Qt::SolidLine, Qt::FlatCap));

	// Horizontal lines
	//
	float y = ToAnalyticCoordinates(QPoint(0, 0)).y();
	int y_min = static_cast<int>(ceil(y));
	y = ToAnalyticCoordinates(QPoint(0, size().height())).y();
	int y_max = static_cast<int>(floor(y));
	for (int i = y_max; i <= y_min; i++)
	{
		int pp = ToCanvasCoordinates(QVector2D(0, i)).y();
		painter.drawLine(0, pp, size().width(), pp);
	}

	// Vertical lines
	//
	float x = ToAnalyticCoordinates(QPoint(0, 0)).x();
	int x_min = static_cast<int>(ceil(x));
	x = ToAnalyticCoordinates(QPoint(size().width(), 0)).x();
	int x_max = static_cast<int>(floor(x));
	for (int i = x_min; i <= x_max; i++)
	{
		int pp = ToCanvasCoordinates(QVector2D(i, 0)).x();
		painter.drawLine(pp, 0, pp, size().height());
	}

	// Axis
	//

	painter.setPen(QPen(FatGridColor, GridWidth, Qt::SolidLine, Qt::FlatCap));
	QPoint p = ToCanvasCoordinates(QVector2D(0,0));
	if (0 <= p.x() && p.x() <= size().width())
		painter.drawLine(p.x(), 0, p.x(), size().height());
	if (0 <= p.y() && p.y() <= size().height())
		painter.drawLine(0, p.y(), size().width(), p.y());

	painter.setRenderHint(QPainter::Antialiasing, true);
	painter.setPen(QPen(Qt::red, 2, Qt::SolidLine, Qt::FlatCap));


	// Curve segments
	//
	constexpr float steps = 40.0f;
	constexpr float step = 1.0f / steps;

	for (float t = step; t <= 1.0f; t+=step)
	{
		QVector2D p0 = currentCurve.Evaluate(t - step);
		QVector2D p1 = currentCurve.Evaluate(t);
		painter.drawLine(ToCanvasCoordinates(p0), ToCanvasCoordinates(p1));
	}
	{
		QVector2D p0 = currentCurve.Evaluate(1.0f - step);
		QVector2D p1 = currentCurve.Evaluate(1.0f);
		painter.drawLine(ToCanvasCoordinates(p0), ToCanvasCoordinates(p1));
	}

	painter.setPen(QPen(Qt::green, 1, Qt::SolidLine, Qt::RoundCap));
	painter.drawLine(ToCanvasCoordinates(currentCurve.A), ToCanvasCoordinates(currentCurve.P1));
	painter.drawLine(ToCanvasCoordinates(currentCurve.B), ToCanvasCoordinates(currentCurve.P2));
	painter.setRenderHint(QPainter::Antialiasing, false);


	// Dots
	//
	QColor col = DotColor;
	QColor colEdge = DotEdgeColor;
	painter.setPen(QPen(colEdge, 1, Qt::SolidLine, Qt::FlatCap));
	painter.setBrush(QBrush(col));

	for (int i = 0; i < 4; i++)
	{
		QColor nextCol = DotColor;
		QColor nextEdgeCol = DotEdgeColor;

		if (mouseUnderPoint[i])
		{
			nextCol = DotSelectionColor;
			nextEdgeCol = DotEdgeSelectionColor;
		}

		if (col != nextCol || colEdge != nextEdgeCol)
		{
			col = nextCol;
			colEdge = nextEdgeCol;
			painter.setPen(QPen(colEdge, 1, Qt::SolidLine, Qt::FlatCap));
			painter.setBrush(QBrush(col));
		}

		QPoint center = ToCanvasCoordinates(currentCurve.dots[i]);
		painter.drawRect(center.x() - DotSize, center.y() - DotSize, DotSize * 2, DotSize * 2);
	}
}

void CurveWidget::mouseReleaseEvent(QMouseEvent *event)
{
	Q_UNUSED(event)
	isDragging = 0;
	dragDotIdx = -1;
}

void CurveWidget::mouseMoveEvent(QMouseEvent *event)
{
	mousePosition = event->pos();

	if (isDragging == 1)
	{
		centerOffset = dragStartPixelsOffset + QVector2D(event->pos()) - QVector2D(dragStartMousePos);
		repaint();
	}
	else if (isDragging == 2)
	{
		if (dragDotIdx >= 0)
		{
			auto newPos = ToAnalyticCoordinates(mousePosition);
			if (currentCurve.dots[dragDotIdx] != newPos)
			{
				currentCurve.dots[dragDotIdx] = newPos;
				repaint();
			}
		}
	}
}

void CurveWidget::wheelEvent(QWheelEvent *event)
{
	int numDegrees = event->delta();
	pixelsInUnitScale *= float((numDegrees > 0) ? 1.05f : 0.95f);
	event->accept();
	repaint();
}

void CurveWidget::resizeEvent(QResizeEvent *event)
{
	float proportionX = static_cast<float>(event->size().width()) / event->oldSize().width();
	float proportionY = static_cast<float>(event->size().height()) / event->oldSize().height();

	if (proportionX >= 0.0001f && proportionY >= 0.0001f)
	{
		centerOffset = QVector2D(centerOffset.x() * proportionX, centerOffset.y() * proportionY);
	}

	QWidget::resizeEvent(event);
}

void CurveWidget::showEvent(QShowEvent *event)
{
	centerOffset = QVector2D(rect().width() * 0.5f, rect().height() * 0.5f);
	NormalizeView();
	QWidget::showEvent(event);
}

void CurveWidget::NormalizeView()
{
	QVector2D bottomLeft = currentCurve.A;
	QVector2D topRight = currentCurve.B;
	QVector2D size_ = topRight - bottomLeft;

	auto minSide = std::min(rect().width(), rect().height());
	auto maxSide = std::max(rect().width(), rect().height());

	float aspectWidget = static_cast<float>(rect().width()) / rect().height();
	float aspect = size_.x() / size_.y();

	qDebug() << "aspectWidget" << aspectWidget << "aspectCurve" << aspect;

//	if (aspectWidget > aspect)
//	{
//		centerOffset = QVector2D((rect().width() - aspect * minSide) * 0.5f, minSide);
//		pixelsInUnitScale = minSide / size_.y();
//	} else
//	{ // todo
//		centerOffset = QVector2D(50, 950);
//		pixelsInUnitScale = minSide;
//	}

	repaint();
}

void CurveWidget::mousePressEvent(QMouseEvent *event)
{
	if (event->button() == Qt::MouseButton::MiddleButton)
	{
		isDragging = 1;
		dragStartMousePos = event->pos();
		dragStartPixelsOffset = centerOffset;
	}
	else if (event->button() == Qt::MouseButton::LeftButton)
	{
		isDragging = 2;
		dragStartMousePos = event->pos();
		for(int i = 0; i < 4; i++)
		{
			if (mouseUnderPoint[i])
			{
				dragDotIdx = i;
				break;
			}
		}
	}
}

QPoint CurveWidget::ToCanvasCoordinates(const QVector2D &pos)
{
	float x = pos.x() * pixelsInUnitScale + centerOffset.x();
	float y = -pos.y() * pixelsInUnitScale + centerOffset.y();
	return QPoint(static_cast<int>(x), static_cast<int>(y));
}

QVector2D CurveWidget::ToAnalyticCoordinates(const QPoint &pos)
{
	return QVector2D((pos.x() - centerOffset.x()) / pixelsInUnitScale, (-pos.y() + centerOffset.y()) / pixelsInUnitScale);
}

