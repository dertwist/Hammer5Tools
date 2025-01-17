#include "CurveWidgetDialog.h"
#include "ui_CurveWidgetDialog.h"
#include <QDesktopWidget>
#include <QRect>

CurveWidgetDialog::CurveWidgetDialog(QWidget *parent) :
	QDialog(parent),
	ui(new Ui::CurveWidgetDialog)
{
	ui->setupUi(this);

	//setWindowFlags(Qt::Tool);
	//setModal(true);

	Qt::WindowFlags flags = windowFlags();
	flags = flags & (~Qt::WindowContextHelpButtonHint);
	flags = flags | (Qt::WindowMaximizeButtonHint);
	setWindowFlags(flags);

	QDesktopWidget *desktop = QApplication::desktop();
	QRect screenSize = desktop->availableGeometry(this);
	resize(screenSize.width() * 0.8f, screenSize.height() * 0.8f);

	Curve c;
	ui->curveWidget->SetCurve(c);
}

CurveWidgetDialog::~CurveWidgetDialog()
{
	delete ui;
}


void CurveWidgetDialog::on_toolButton_clicked()
{
	ui->curveWidget->NormalizeView();
}
