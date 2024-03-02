"use client"

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { ColumnDef } from "@tanstack/react-table"
import { ArrowUpDown } from "lucide-react";

import * as React from "react";

export type Transaction = {
    "Datum": Date
    "Auftraggeber / Empfänger": string
    "Verwendungszweck": string
    "IBAN / Kontonummer": string
    "Betrag": number
};


import { Column } from "@tanstack/react-table";
import { AccountCategorySelector } from "@/components/ui-composition/category-selector";

type SortableColumnHeaderProps = {
  column: Column<Transaction>;
}

const SortableColumnHeader = ({ column }: SortableColumnHeaderProps) => {
  return (
    <Button variant="ghost" onClick={() => {
      column.toggleSorting(column.getIsSorted() === "asc")
    }}>
      {column.id}
      <ArrowUpDown className="ml-2 h-4 w-4" />
    </Button>
  )
}

export const columns: ColumnDef<Transaction>[] = [
  {
    id: "select",
    header: ({ table }) => {
      return (<Checkbox
        checked={table.getIsAllRowsSelected()}
        onCheckedChange={(value) => {
          table.toggleAllRowsSelected(!!value);
        }}
      />)
    },
    cell: ({ row }) => {
      return (<Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => {
          row.toggleSelected(!!value);
        }}
      />)
    },
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "Datum",
    id: "Date",
    header: SortableColumnHeader,
  },
  {
    accessorKey: "Auftraggeber / Empfänger",
    id: "Payee",
    header: SortableColumnHeader,
    cell: ({ getValue, row: { index }, column: { id }, table}) => {
      const initialValue = getValue() as string
      const [value, setValue] = React.useState(initialValue)

      const onBlur = () => {
        table.options.meta?.updateData(index, id, value)
      }

      React.useEffect(() => {
        setValue(initialValue)
      }, [initialValue])

      return (
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onBlur={onBlur}
        />
      )
    }
  },
  {
    accessorKey: "Verwendungszweck",
    id: "Narration",
    header: SortableColumnHeader,
  },
  {
    accessorKey: "expense-category",
    id: "Expense Category",
    header: SortableColumnHeader,
    cell: () => {
      return (
        <AccountCategorySelector />
      )
    },
  },
  // {
  //   accessorKey: "IBAN / Kontonummer",
  //   header: "IBAN",
  // },
  {
    accessorKey: "Betrag",
    id: "Amount",
    header: SortableColumnHeader,
  }
]
