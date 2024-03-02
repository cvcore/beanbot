"use client"

import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import * as React from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { ModeToggle } from "@/components/mode-toggle"
import { AxeIcon, BookIcon, DeleteIcon, PenIcon, TrashIcon } from "lucide-react"
import { BatchEditDialogMenuItem } from "@/components/ui-composition/batch-edit"

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
}

export function TransactionDataTable<TData, TValue>({
  columns,
  data,
}: DataTableProps<TData, TValue>) {

  const [sorting, setSorting] = React.useState<SortingState>([])
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])
  const [rowSelection, setRowSelection] = React.useState({})
  const [varData, setData] = React.useState(data)

  console.log(rowSelection) // grab row Selection state from here!

  const table = useReactTable({
    data: varData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),

    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onRowSelectionChange: setRowSelection,

    state: {
      sorting,
      columnFilters,
      rowSelection,
    },

    meta: {
      updateData: (rowIndex, columnId, value) => {
        // skipAutoResetPageIndex()
        setData(old =>
          old.map((row, index) => {
            if (index === rowIndex) {
              return {
                ...old[rowIndex]!,
                [columnId]: value,
              }
            }
            return row
          })
        )
      }
    },
  })

  return (
    <>
      <div className="rounded-md">
        <div className="flex items-center py-4">
          <Input
            placeholder="Filter Payee"
            value={table.getColumn("Payee")?.getFilterValue() as string || ""}
            onChange={(e) => {
              table.getColumn("Payee")?.setFilterValue(e.target.value);
            }}
            className="max-w-sm"
          />

          {/* Provide a dropdown menu to select visible columns */}
          {/* we need to use the asChild prop as we are replacing the default rendered child in DropdownMenuTrigger with our customized Button */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="ml-4">Columns</Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {table
                .getAllColumns()
                .filter(column => column.getCanHide())
                .map(column => {
                  return (
                    <DropdownMenuCheckboxItem
                      key={column.id}
                      className="capitalize"
                      checked={column.getIsVisible()}
                      onCheckedChange={(value: boolean) => {
                        column.toggleVisibility(!!value);
                      }}
                    >
                      {column.id}
                    </DropdownMenuCheckboxItem>
                  );
                })
              }
            </DropdownMenuContent>
          </DropdownMenu>

          <div className="flex items-center ml-auto">
            <div className="mr-4">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="destructive"
                    color="danger"
                    className={
                      table.getSelectedRowModel().rows.length === 0 ? "hidden" : ""
                    }>
                    <AxeIcon className="mr-2" />Actions
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => {console.log("TODO: delete selected rows!")}}><TrashIcon className="mr-2" />Delete Selected</DropdownMenuItem>
                  <BatchEditDialogMenuItem />
                  <DropdownMenuItem><BookIcon className="mr-2" />Commit Selected</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <div><ModeToggle /></div>
          </div>

        </div>
      </div>

      <div className="rounded-md border">
        {/* Provide an input box for entering the filter criterions of the payee */}
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                        )
                      }
                    </TableHead>
                  )
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id} data-state={row.getIsSelected() && "selected"}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {/* Here we print the number of selected rows and total number of rows */}
        <div className="flex-1 text-sm text-muted-foreground ml-4 py-4">
          Selected {table.getFilteredSelectedRowModel().rows.length} out of {" "}
          {table.getFilteredRowModel().rows.length} rows.
        </div>
      </div>
    </>
  )
}
