declare const config: {
    content: string[];
    theme: {
        extend: {
            colors: {
                border: string;
                background: string;
                foreground: string;
                muted: string;
                card: string;
                accent: string;
                ring: string;
            };
            boxShadow: {
                panel: string;
            };
        };
    };
    plugins: any[];
};
export default config;
