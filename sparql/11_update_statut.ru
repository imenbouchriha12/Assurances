# UPDATE : faire passer un sinistre de "Declare" a "EnExpertise" et lui affecter un expert
PREFIX :     <http://www.semanticweb.org/ontologies/assurance-sinistres#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>

DELETE { :Sinistre_2026_011 :statutSinistre ?ancien }
INSERT { :Sinistre_2026_011 :statutSinistre "EnExpertise" ; :estExpertisePar :Expert_Leila }
WHERE  { :Sinistre_2026_011 :statutSinistre ?ancien }
