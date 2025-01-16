#include "MainWindow.h"
#include "CurveWidgetDialog.h".h"
#include <QApplication>

int main(int argc, char *argv[])
{
	QApplication a(argc, argv);

	CurveWidgetDialog w;
	w.show();

	return a.exec();
}
