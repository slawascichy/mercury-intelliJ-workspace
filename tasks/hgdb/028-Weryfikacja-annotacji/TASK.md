# [28] Weryfikacja annotacji @NameRepresentation

Zadanie z https://github.com/slawascichy/hgdb/issues/28


## Cel

Trzeba zweryfikować ustawienia annotacji `@NameRepresentation` w encjach czy jest zgodna z ustawieniami w metodzie getName() np. w encji ArchCase mamy:

`@NameRepresentation(referencedFieldName = "coalesce(" + MDictDAO.DEFAULT_ALIAS + ".inventoryCode, 'CID:'||"
		+ MDictDAO.DEFAULT_ALIAS + ".id)||' '||" + MDictDAO.DEFAULT_ALIAS + ".type.typeName")`

a w metodzie {{getName()}} jest:
`	public String getName() {
		return new StringBuilder(
				(StringUtils.isNotBlank(this.inventoryCode) ? this.inventoryCode : ID_PREFIX + this.id))
						.append(MercuryConfig.SPACE)
						.append((this.type != null && StringUtils.isNotBlank(this.type.getTypeName())
								? this.type.getTypeName() : StringUtils.EMPTY))
						.toString();

	}`
Czyli jest OK, ale czy wszystkie encje mają poprawnie zbudowaną definicję annotacji? To trzeba sprawdzić.

## Status

Zrobione