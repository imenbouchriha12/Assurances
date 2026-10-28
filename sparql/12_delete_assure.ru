# DELETE : supprimer un assure et tous ses triplets (sujet et objet)
PREFIX :     <http://www.semanticweb.org/ontologies/assurance-sinistres#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>

DELETE WHERE { :Assure_Test ?p ?o } ;
DELETE WHERE { ?s ?p :Assure_Test }
