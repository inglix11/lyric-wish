#!/usr/ali/bin/python
# coding=utf-8

'''Write contents into a excel file(.xls)

Eample:
    $ from pypet.common.excel import ExcelW
    $ excel = ExcelW()
    $ excel.add_sheet(
        sheet_name = 'summary',
        head = ['No','Name','Qty.','Amount','Date/Time'],
        rows = [
            (1, u'测试人员',12,.6, '2010/10/31'),
            (2,'Bruce Wang',16,.8,'2010-10-31'),
            (3,'Hans Wang',10,.5,'2010-11-12 12:32:23'),
        ])
    $ excel.save('example.xls')
'''

# Can be 'Prototype', 'Development', 'Product'
__status__ = 'Development'
__author__ = 'tuantuan.lv <tuantuan.lv@alibaba-inc.com>'

import xlwt

class ExcelW:
    def __init__(self):
        self.book = xlwt.Workbook()

    def add_sheet(self, sheet_name, head, rows):
        sheet = self.book.add_sheet(sheet_name)
        i = j = 0

        for value in head:
            sheet.write(i, j, value)
            j += 1

        for row in rows:
            i += 1
            j = 0

            for value in row:
                sheet.write(i, j, value)
                j += 1

    def save(self, filename):
        self.book.save(filename)

if __name__ == '__main__':
    excel = ExcelW()

    excel.add_sheet(
        sheet_name = 'summary',
        head = ['No','Name','Qty.','Amount','Date/Time'],
        rows = [
            (1, u'测试人员',12,.6, '2010/10/31'),
            (2,'Bruce Wang',16,.8,'2010-10-31'),
            (3,'Hans Wang',10,.5,'2010-11-12 12:32:23'),
        ])

    excel.save('example.xls')
