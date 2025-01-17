#include "MainWindow.h"
#include "ui_MainWindow.h"
#include "CurveWidgetDialog.h"

MainWindow::MainWindow(QWidget *parent) :
	QMainWindow(parent),
	ui(new Ui::MainWindow)
{
	ui->setupUi(this);
}

MainWindow::~MainWindow()
{
	delete ui;
}

void MainWindow::on_pushButton_clicked()
{
	CurveWidgetDialog myNewDialog(this);
	myNewDialog.show();
	myNewDialog.exec();
}

