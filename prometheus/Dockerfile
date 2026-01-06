FROM prom/prometheus:v2.48.1

# Copia a configuração do Prometheus
COPY prometheus.yml /etc/prometheus/prometheus.yml

# Expõe a porta padrão do Prometheus
EXPOSE 9090

# Volume para dados do Prometheus
VOLUME ["/prometheus"]

# Configura permissões e inicia o Prometheus
USER root
RUN chown -R nobody:nobody /etc/prometheus /prometheus
USER nobody

ENTRYPOINT ["/bin/prometheus"]
CMD ["--config.file=/etc/prometheus/prometheus.yml", \
     "--storage.tsdb.path=/prometheus", \
     "--web.console.libraries=/usr/share/prometheus/console_libraries", \
     "--web.console.templates=/usr/share/prometheus/consoles", \
     "--web.enable-lifecycle", \
     "--storage.tsdb.retention.time=30d"]
