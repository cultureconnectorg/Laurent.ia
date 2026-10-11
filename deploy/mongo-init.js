// Runs once, at first start of an empty database. One user per system, each limited
// to its own database: Laurent.ia cannot read FREKCORE's data and vice versa.
const env = process.env;
db.getSiblingDB("laurentia").createUser({
  user: "laurentia", pwd: env.LAURENTIA_DB_PASSWORD,
  roles: [{ role: "readWrite", db: "laurentia" }],
});
db.getSiblingDB("frekcore").createUser({
  user: "frekcore", pwd: env.FREKCORE_DB_PASSWORD,
  roles: [{ role: "readWrite", db: "frekcore" }],
});
