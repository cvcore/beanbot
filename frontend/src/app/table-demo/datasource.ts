// import data from my csv file into a json object

import * as fs from 'fs';
import * as Papa from 'papaparse';
import * as path from 'path';
import { Transaction } from './columns';


export function parseCSV(filePath: string): Promise<Transaction[]> {
    return new Promise((resolve, reject) => {
        const csvData = fs.readFileSync(filePath, { encoding: 'latin1' });

        Papa.parse<Transaction>(csvData, {
            header: true,
            complete: (result) => {
                if (result.errors.length === 0) {
                    resolve(result.data);
                } else {
                    reject(result.errors);
                }
            },
            skipEmptyLines: true,
        });
    });
}
