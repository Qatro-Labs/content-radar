// DESIGN.md §4, «Vistazo»: mientras la persona mira un tema citado, la barra de Rad se vuelve
// transparente y todo lo que no son los chips de «Citadas» casi desaparece, para que se vea la
// página de detrás. La barra es el `group/dock` y marca el vistazo con `data-peeking`.
//
// La opacidad no se hereda hacia arriba: un padre a 0.1 apagaría también los chips. Por eso se
// atenúa cada parte hermana de los chips, nunca uno de sus contenedores. Y van en un elemento
// sin la entrada de `TEXT_ENTER_CLASS`: su `duration-300` pisaría los 150 ms de este fundido.
const PEEK_FADE_CLASS = 'transition-opacity duration-150 ease-out motion-reduce:transition-none'

export const PEEK_DIM_CLASS = `${PEEK_FADE_CLASS} group-data-peeking/dock:opacity-10`
// El campo baja menos: sigue marcando dónde está la barra mientras se mira la página.
export const PEEK_DIM_COMPOSER_CLASS = `${PEEK_FADE_CLASS} group-data-peeking/dock:opacity-35`
