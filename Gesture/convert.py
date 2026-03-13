import csv

inx = 1
labels = {}

with open("data_test.csv", 'r') as f1, open("data_test_convted.csv", 'w') as f2:
    reader = csv.reader(f1)
    writer = csv.writer(f2, lineterminator='\n')
    for row in reader:
        if not row[-1] in labels.keys():
            labels[row[-1]] = inx
            inx += 1

        row[-1] = labels[row[-1]]
        writer.writerow(row)
    