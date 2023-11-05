import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { DropdownMenuItem } from "../ui/dropdown-menu"
import { MinusCircleIcon, MinusIcon, PenIcon } from "lucide-react"


import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"


const propertyChanges = [
  {
    property: "Date",
    changeTo: "2023-01-01",
  },
  {
    property: "Category",
    changeTo: "Expenses:Food",
  }
]

export function TableDemo() {
  return (
    <Table>
      {/* <TableCaption>A list of your recent invoices.</TableCaption> */}
      <TableHeader>
        <TableRow>
          <TableHead className="w-[100px]"></TableHead>
          <TableHead>Column</TableHead>
          <TableHead>Change all to</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {propertyChanges.map((pc) => (
          <TableRow key={pc.property}>
            <TableCell className="font-small"><Button variant="ghost"><MinusCircleIcon /></Button></TableCell>
            <TableCell>{pc.property}</TableCell>
            <TableCell>{pc.changeTo}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}


export function BatchEditDialogMenuItem() {
  return (
    <Dialog>
      <DialogTrigger onSelect={(e) => e.preventDefault()}>
        <DropdownMenuItem onSelect={(e) => e.preventDefault()}><PenIcon className="mr-2" />Edit Profile</DropdownMenuItem>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Batch edit properties</DialogTitle>
          <DialogDescription>
            Make changes to all selected rows here. Click save when you're done.
          </DialogDescription>
        </DialogHeader>
        <TableDemo />
        <DialogFooter>
          <div className="flex items-center">
            <Button type="submit" variant="outline">Add property</Button>
            <Button className="ml-4" type="submit">Save changes</Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
