FROM prom/pushgateway:v1.7.0

# Expõe a porta padrão do Pushgateway
EXPOSE 9091

# Configura o Pushgateway para aceitar requisições de qualquer origem
# Útil quando o listener está em um container/servidor diferente
ENTRYPOINT ["/bin/pushgateway"]
CMD ["--web.listen-address=:9091", \
     "--web.enable-lifecycle", \
     "--web.enable-admin-api", \
     "--persistence.file=/data/pushgateway.data", \
     "--persistence.interval=5m"]

# Volume para persistir métricas entre restarts
VOLUME ["/data"]
