# CREATE : ajouter un nouvel assure
PREFIX :     <http://www.semanticweb.org/ontologies/assurance-sinistres#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>

INSERT DATA {
  :Assure_Test a :Assure, :Personne ;
      :nom "Test" ; :prenom "Nour" ; :cin "12345699" ; :adresse "Bizerte" .
}
