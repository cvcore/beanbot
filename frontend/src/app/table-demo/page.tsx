import Image from 'next/image'
import { parseCSV } from './datasource';
import { TransactionDataTable } from './data-table';
import { Transaction, columns } from './columns';
import { ModeToggle } from '@/components/mode-toggle';

export default async function Home() {
  let txnData: Transaction[] = [];

  try {
    txnData = await parseCSV('/Users/core/Development/Web/shadcn-table-demo/data/data.csv')
  } catch (error) {
    console.error(error)
  }

  return (
    <>
      <div className='text-red-600 text-center'>Hello, page under construction!</div>
      <br />
      <div className='container mx-auto py-10'>
        <TransactionDataTable columns={columns} data={txnData} />
      </div>
    </>
  )
}
