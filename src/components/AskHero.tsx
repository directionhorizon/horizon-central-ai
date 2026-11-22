/**
 * Référence « Ask me anything » : accueil conversationnel épuré.
 * L'onde n'est animée que pendant une demande réelle (`active`), sinon elle reste
 * statique et atténuée : aucune animation décorative permanente.
 */
export function AskHero({ active, modelReady }: { active: boolean; modelReady: boolean }) {
  const traces = [0, 1, 2, 3, 4, 5];
  return (
    <div className="ask-hero">
      <div className={active ? 'ask-frame ask-frame--active' : 'ask-frame'}>
        <h1 id="workbench-title" className="ask-title">
          {active ? 'HORIZON traite votre demande…' : 'Demandez ce que vous voulez…'}
        </h1>
        <svg
          className={active ? 'ask-wave ask-wave--active' : 'ask-wave'}
          viewBox="0 0 320 32"
          role="img"
          aria-label={active ? 'Demande en cours de traitement' : 'Aucune demande en cours'}
        >
          {traces.map((index) => {
            // Au repos, l'amplitude est quasi nulle : une ligne, pas une fausse
            // ondulation. Pendant une demande réelle, l'onde s'anime franchement.
            const amplitude = active ? 1 - index * 0.13 : 0.12;
            return (
              <path
                key={index}
                d={`M4 16 C 40 ${16 - 12 * amplitude}, 70 ${16 + 12 * amplitude}, 110 16
                    S 180 ${16 - 12 * amplitude}, 220 16
                    S 290 ${16 + 12 * amplitude}, 316 16`}
                fill="none"
                stroke="currentColor"
                strokeWidth={1.2}
                strokeLinecap="round"
                opacity={active ? 0.9 - index * 0.13 : 0.45 - index * 0.06}
                style={{ animationDelay: `${index * 90}ms` }}
              />
            );
          })}
        </svg>
        <p className="ask-hint">
          {active
            ? 'Requête en cours auprès du moteur local.'
            : modelReady
              ? 'Fournisseur IA prêt : votre message sera envoyé au modèle.'
              : 'Aucun fournisseur IA disponible : le message sera enregistré sans réponse.'}
        </p>
      </div>
    </div>
  );
}

export default AskHero;