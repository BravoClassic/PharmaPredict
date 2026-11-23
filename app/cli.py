"""Small CLI to exercise the first MySQL-backed vertical slice."""
from __future__ import annotations

import argparse

from .db import make_session_factory, session_scope
from .repositories import InventoryRepository
from .services import InventoryService


def main() -> None:
    parser = argparse.ArgumentParser(prog="pharmapredict")
    sub = parser.add_subparsers(dest="command", required=True)

    stock = sub.add_parser("stock", help="show current inventory summary")
    stock.add_argument("--pharmacy", default="LOC001")

    fefo = sub.add_parser("fefo", help="show FEFO-eligible batches")
    fefo.add_argument("medication_id")
    fefo.add_argument("--pharmacy", default="LOC001")

    dispense = sub.add_parser("dispense", help="post a FEFO dispense transaction")
    dispense.add_argument("medication_id")
    dispense.add_argument("quantity", type=int)
    dispense.add_argument("--rx", required=True)
    dispense.add_argument("--employee", default="EMP003")
    dispense.add_argument("--pharmacy", default="LOC001")

    args = parser.parse_args()
    factory = make_session_factory()

    with session_scope(factory) as session:
        repo = InventoryRepository(session)
        service = InventoryService(session)

        if args.command == "stock":
            for item in repo.inventory_summary(args.pharmacy):
                print(item)
        elif args.command == "fefo":
            for batch in service.fefo_batches(args.pharmacy, args.medication_id):
                print(batch)
        elif args.command == "dispense":
            for movement in service.dispense(
                pharmacy_id=args.pharmacy,
                medication_id=args.medication_id,
                quantity=args.quantity,
                rx_number=args.rx,
                employee_id=args.employee,
            ):
                print(movement)


if __name__ == "__main__":
    main()
