from django.core.management.base import BaseCommand

from hordak.models import Account

CHART: list[tuple[str, str, str, list[tuple[str, str]]]] = [
    (
        "1",
        "ACTIVO",
        "AS",
        [
            (".01", "Caja"),
            (".02", "Valores a Depositar"),
            (".03", "Valores Diferidos a Depositar"),
            (".04", "Bancos"),
            (".05", "Tarjetas de Crédito"),
            (".06", "Deudores por Ventas"),
            (".07", "Deudores Varios"),
            (".08", "Documentos a Cobrar"),
            (".09", "Mercaderías"),
            (".10", "Materias Primas"),
            (".11", "Inmuebles"),
            (".12", "Rodados"),
            (".13", "Muebles y Útiles"),
            (".14", "Instalaciones"),
            (".15", "Maquinarias"),
            (".16", "Equipos de Computación"),
            (".17", "IVA Crédito Fiscal"),
        ],
    ),
    (
        "2",
        "PASIVO",
        "LI",
        [
            (".01", "Proveedores"),
            (".02", "Acreedores Varios"),
            (".03", "Documentos a Pagar"),
            (".04", "Valores Diferidos a Pagar"),
            (".05", "IVA Débito Fiscal"),
            (".06", "IVA Saldo a Pagar"),
        ],
    ),
    (
        "3",
        "PATRIMONIO NETO",
        "EQ",
        [
            (".01", "Capital"),
            (".02", "Resultado del Ejercicio"),
        ],
    ),
    (
        "4",
        "RESULTADOS NEGATIVOS",
        "EX",
        [
            (".01", "Costo de Mercaderías Vendidas"),
            (".02", "Alquileres Perdidos"),
            (".03", "Intereses Perdidos"),
            (".04", "Sueldos y Jornales"),
            (".05", "Fletes y Acarreos"),
            (".06", "Comisiones Perdidas"),
            (".07", "Descuentos Cedidos"),
            (".08", "Publicidad Perdida"),
            (".09", "Gastos Generales"),
            (".10", "Impuestos"),
            (".11", "Seguros"),
        ],
    ),
    (
        "5",
        "RESULTADOS POSITIVOS",
        "IN",
        [
            (".01", "Ventas"),
            (".02", "Alquileres Ganados"),
            (".03", "Intereses Ganados"),
            (".04", "Descuentos Obtenidos"),
            (".05", "Comisiones Ganadas"),
        ],
    ),
]


class Command(BaseCommand):
    help = (
        "Load the base chart of accounts for the SIC system (levels 1 and 2). "
        "Safe to run multiple times: existing accounts are not duplicated."
    )

    def handle(self, *args, **options) -> None:
        created_roots = 0
        created_children = 0

        for root_code, root_name, account_type, children in CHART:
            root, was_created = self._ensure_root(root_code, root_name, account_type)
            if was_created:
                created_roots += 1
                self.stdout.write(f"  Created root: {root_code} {root_name}")

            for child_code, child_name in children:
                _, child_created = self._ensure_child(root, child_code, child_name)
                if child_created:
                    created_children += 1
                    full = f"{root_code}{child_code}"
                    self.stdout.write(f"    Created: {full} {child_name}")

        if created_roots == 0 and created_children == 0:
            self.stdout.write(
                self.style.WARNING("Chart of accounts already loaded. Nothing to do.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Created {created_roots} root(s) and {created_children} account(s)."
                )
            )

    def _ensure_root(self, code: str, name: str, account_type: str) -> tuple[Account, bool]:
        # Hordak full_code is built by trigger from local code segments.
        try:
            account = Account.objects.get(code=code, parent=None)
            return account, False
        except Account.DoesNotExist:
            account = Account.objects.create(
                code=code,
                name=name,
                type=account_type,
                currencies=["ARS"],
            )
            return account, True

    def _ensure_child(self, parent: Account, code: str, name: str) -> tuple[Account, bool]:
        # Child local codes keep dot-prefix format (e.g. ".04") for trigger composition.
        try:
            account = Account.objects.get(code=code, parent=parent)
            return account, False
        except Account.DoesNotExist:
            account = Account.objects.create(
                code=code,
                name=name,
                type=parent.type,
                currencies=parent.currencies,
                parent=parent,
            )
            return account, True
